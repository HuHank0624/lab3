# path: server/handlers.py
from typing import Dict, Any

from utils.file_transfer import decode_chunk, encode_chunk
from utils.protocol import send_error, send_ok, send_json, recv_json

from .auth import AuthManager
from .data import DataStore
from .game_manager import GameManager
from .lobby_manager import LobbyManager
from .utils import log
import os
class RequestHandlers:
    def __init__(
        self,
        datastore: DataStore,
        auth: AuthManager,
        games: GameManager,
        lobby: LobbyManager,
    ):
        self.datastore = datastore
        self.auth = auth
        self.games = games
        self.lobby = lobby

    # ---- main entry ----
    def handle(self, sock, conn_id: int, msg: Dict[str, Any]) -> None:
        try:
            action = msg.get("action")
            log(f"[conn {conn_id}] action={action} payload={msg}")

            if action == "register":
                self._handle_register(sock, msg)
                return

            if action == "login":
                self._handle_login(sock, conn_id, msg)
                return

            # Require login for everything else
            sess = self.auth.require_login(conn_id)
            if not sess:
                send_error(sock, "Not logged in")
                return

            role = sess["role"]
            username = sess["username"]

            # ---- dispatch ----
            if action == "list_games":
                self._handle_list_games(sock)

            elif action == "upload_game_init" and role == "developer":
                self._handle_upload_init(sock, username, msg)

            elif action == "upload_game_chunk" and role == "developer":
                self._handle_upload_chunk(sock, msg)

            elif action == "submit_review" and role == "player":
                self._handle_submit_review(sock, username, msg)

            elif action == "list_rooms":
                self._handle_list_rooms(sock)

            elif action == "create_room" and role == "player":
                self._handle_create_room(sock, username, msg)

            elif action == "join_room" and role == "player":
                self._handle_join_room(sock, username, msg)

            elif action == "leave_room" and role == "player":
                self._handle_leave_room(sock, username, msg)

            elif action == "start_game" and role == "player":
                self._handle_start_game(sock, username, msg)

            elif action == "download_game" and role == "player":
                self._handle_download_game(sock, username, msg)

            else:
                send_error(sock, f"Unknown or unauthorized action: {action}")

        except Exception as e:
            log(f"[ERROR] handler exception: {e}")
            try:
                send_error(sock, f"Server error: {e}")
            except Exception:
                pass  # socket may already be closed

    # ---- basic auth ----

    def _handle_register(self, sock, msg: Dict[str, Any]) -> None:
        username = msg.get("username", "").strip()
        password = msg.get("password", "")
        role = msg.get("role", "")

        if role not in ("player", "developer"):
            send_error(sock, "Invalid role")
            return
        if not username or not password:
            send_error(sock, "Username and password required")
            return

        resp = self.auth.register(username, password, role)
        if resp["status"] == "ok":
            send_ok(sock, message=resp["message"])
        else:
            send_error(sock, resp["message"])

    def _handle_login(self, sock, conn_id: int, msg: Dict[str, Any]) -> None:
        username = msg.get("username", "").strip()
        password = msg.get("password", "")
        role = msg.get("role", "")

        resp = self.auth.login(conn_id, username, password, role)
        if resp["status"] == "ok":
            send_ok(sock, username=resp["username"], role=resp["role"])
        else:
            send_error(sock, resp["message"])

    # ---- games & store ----

    def _handle_list_games(self, sock) -> None:
        games = self.games.list_games()
        send_ok(sock, games=games)

    def _handle_upload_init(self, sock, developer: str, msg: Dict[str, Any]) -> None:
        name = msg.get("name", "").strip()
        version = msg.get("version", "").strip()
        description = msg.get("description", "").strip()
        cli_entry = msg.get("cli_entry", "").strip()
        gui_entry = msg.get("gui_entry", "").strip()

        if not name or not version:
            send_error(sock, "name and version are required")
            return

        upload_id, chunk_size, _ = self.games.start_upload(
            developer=developer,
            name=name,
            version=version,
            description=description,
            cli_entry=cli_entry,
            gui_entry=gui_entry,
        )
        send_ok(sock, upload_id=upload_id, chunk_size=chunk_size)

    def _handle_upload_chunk(self, sock, msg: Dict[str, Any]) -> None:
        upload_id = msg.get("upload_id")
        data_b64 = msg.get("data")
        eof = bool(msg.get("eof", False))

        if not upload_id or data_b64 is None:
            send_error(sock, "upload_id and data are required")
            return

        try:
            raw = decode_chunk(data_b64)
        except Exception as e:
            send_error(sock, f"Invalid base64 data: {e}")
            return

        err = self.games.write_upload_chunk(upload_id, raw, eof)
        if err:
            send_error(sock, err)
        else:
            send_ok(sock, finished=eof)

    def _handle_submit_review(self, sock, username: str, msg: Dict[str, Any]) -> None:
        game_id = msg.get("game_id")
        rating = int(msg.get("rating", 0))
        comment = msg.get("comment", "").strip()

        if not game_id or not (1 <= rating <= 5):
            send_error(sock, "Invalid review")
            return

        ok = self.games.add_review(game_id, username, rating, comment)
        if ok:
            send_ok(sock)
        else:
            send_error(sock, "Game not found")

    # ---- lobby / rooms ----

    def _handle_list_rooms(self, sock) -> None:
        rooms = self.lobby.list_rooms()
        send_ok(sock, rooms=rooms)

    def _handle_create_room(self, sock, username: str, msg: Dict[str, Any]) -> None:
        game_id = msg.get("game_id")
        room_name = msg.get("room_name", "Room")
        max_players = int(msg.get("max_players", 2))

        if not game_id:
            send_error(sock, "game_id required")
            return

        game = self.games.get_game(game_id)
        if not game:
            send_error(sock, "Game not found")
            return

        user = self.datastore.get_user(username)
        owned = (user or {}).get("owned_games", [])
        if game_id not in owned:
            send_error(sock, "You must download the game before creating room")
            return

        port = self.games.allocate_game_port()
        resp = self.lobby.create_room(
            host_username=username,
            game_id=game_id,
            room_name=room_name,
            max_players=max_players,
            game_port=port,
        )
        send_ok(sock, **resp)

    def _handle_join_room(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return

        resp = self.lobby.join_room(room_id, username)
        if resp["status"] == "ok":
            send_ok(sock, room_info=resp["room_info"])
        else:
            send_error(sock, resp["message"])

    def _handle_leave_room(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return

        self.lobby.leave_room(room_id, username)
        send_ok(sock)

    def _handle_start_game(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return

        resp = self.lobby.start_game(room_id)
        if resp["status"] == "ok":
            send_ok(sock, **resp)
        else:
            send_error(sock, resp["message"])

    # ---- download ----

    def _handle_download_game(self, sock, username: str, msg: Dict[str, Any]) -> None:
        game_id = msg.get("game_id")
        if not game_id:
            send_error(sock, "game_id required")
            return

        game = self.games.get_game(game_id)
        if not game:
            send_error(sock, "Game not found")
            return

        # 權限檢查（你原本就有）
        user = self.datastore.get_user(username)
        owned = (user or {}).get("owned_games", [])
        if game_id not in owned:
            send_error(sock, "You must download the game first")
            return

        zip_path = game["file_path"]
        if not os.path.exists(zip_path):
            send_error(sock, "Game file missing on server")
            return

        # 🔥 真正開始傳檔
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    send_json(sock, {
                        "action": "download_chunk",
                        "eof": True
                    })
                    break

                send_json(sock, {
                    "action": "download_chunk",
                    "data": encode_chunk(chunk),
                    "eof": False
                })
