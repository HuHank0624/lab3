# path: server/game_manager.py
import os
import threading
import uuid
from typing import Dict, Any, Optional, Tuple

from .data import DataStore
from .utils import STORAGE_DIR, log


class UploadSession:
    """State for one ongoing chunked upload."""

    def __init__(
        self,
        upload_id: str,
        developer: str,
        name: str,
        version: str,
        description: str,
        cli_entry: str,
        gui_entry: str,
        target_path: str,
    ):
        self.upload_id = upload_id
        self.developer = developer
        self.name = name
        self.version = version
        self.description = description
        self.cli_entry = cli_entry
        self.gui_entry = gui_entry
        self.target_path = target_path
        self.file = open(target_path, "wb")
        self.lock = threading.Lock()
        self.finished = False

    def write_chunk(self, chunk: bytes, eof: bool) -> None:
        """Write one chunk of data; close file on EOF."""
        with self.lock:
            if self.finished:
                return
            self.file.write(chunk)
            if eof:
                self.file.flush()
                self.file.close()
                self.finished = True


class GameManager:
    """Handle game metadata and upload sessions."""

    def __init__(self, datastore: DataStore, base_port: int = 10002):
        self.datastore = datastore
        self.uploads: Dict[str, UploadSession] = {}
        self.uploads_lock = threading.Lock()

        self.base_port = base_port
        self.port_lock = threading.Lock()
        self.next_port = base_port

    # ---------- Upload handling ----------

    def start_upload(
        self,
        developer: str,
        name: str,
        version: str,
        description: str,
        cli_entry: str,
        gui_entry: str,
    ) -> Tuple[str, int, str]:
        """
        Create a new upload session.
        Returns (upload_id, chunk_size, target_path)
        """
        upload_id = uuid.uuid4().hex
        filename = f"{upload_id}.zip"
        target_path = os.path.join(STORAGE_DIR, filename)
        # chunk size chosen arbitrarily; clients should respect this value
        chunk_size = 4096

        sess = UploadSession(
            upload_id=upload_id,
            developer=developer,
            name=name,
            version=version,
            description=description,
            cli_entry=cli_entry,
            gui_entry=gui_entry,
            target_path=target_path,
        )
        with self.uploads_lock:
            self.uploads[upload_id] = sess
        log(f"Upload session created: {upload_id} -> {target_path}")
        return upload_id, chunk_size, target_path

    def write_upload_chunk(self, upload_id: str, chunk: bytes, eof: bool) -> Optional[str]:
        """Append a chunk to the upload; on EOF finalize and register game."""
        with self.uploads_lock:
            sess = self.uploads.get(upload_id)
        if not sess:
            return "Invalid upload_id"
        sess.write_chunk(chunk, eof)
        if eof:
            # finalize: register / update game in datastore
            game_id = self.datastore.add_or_update_game(
                developer=sess.developer,
                name=sess.name,
                version=sess.version,
                description=sess.description,
                file_path=sess.target_path,
                cli_entry=sess.cli_entry,
                gui_entry=sess.gui_entry,
            )
            # after finalize, remove from active uploads
            with self.uploads_lock:
                self.uploads.pop(upload_id, None)
            log(f"Upload {upload_id} finished, registered as game {game_id}")
        return None

    # ---------- Game listing / reviews wrappers ----------

    def list_games(self):
        return self.datastore.list_games()

    def get_game(self, game_id: str):
        return self.datastore.get_game(game_id)

    def add_review(self, game_id: str, username: str, rating: int, comment: str) -> bool:
        return self.datastore.add_review(game_id, username, rating, comment)

    # ---------- Game server port allocation ----------

    def allocate_game_port(self) -> int:
        """
        Allocate a unique TCP port for a game room.
        Ports start from base_port (>= 10000).
        """
        with self.port_lock:
            port = self.next_port
            self.next_port += 1
        log(f"Allocated game port: {port}")
        return port

    # 🎯 說明：
    # 這個 GameManager 負責：
    # - 管理上架/更新遊戲 metadata
    # - 管理 chunked upload 的 session
    # - 分配每個房間的 game_port
    #
    # 真正「啟動某遊戲的 game server subprocess」會依照你們遊戲的實作方式不同，
    # 比較適合在之後的版本裡、根據實際的 game server 路徑再補上：
    #
    # 例如未來可以長這樣：
    #
    #   def start_game_server(self, game_id: str, room_id: str, port: int) -> None:
    #       # 1. 查出該 game 的檔案路徑與 entry script
    #       # 2. 用 subprocess.Popen([...]) 開一個獨立的 game_server.py
    #       # 3. 把 room_id / port 傳進去，讓遊戲自己處理玩家同步
    #
    # 目前 platform 端只需要 port，Player client 連到這個 port 即可。
