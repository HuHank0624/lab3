# path: server/handlers.py
from typing import Dict, Any

from utils.file_transfer import decode_chunk
from utils.protocol import send_json, send_error, send_ok

from .auth import AuthManager
from .data import DataStore
from .game_manager import GameManager
from .lobby_manager import LobbyManager
from .utils import log


class RequestHandlers:
    def __init__(self, datastore: DataStore, auth: AuthManager, games: GameManager, lobby: LobbyManager):
        self.datastore = datastore
        self.auth = auth
        self.games = games
        self.lobby = lobby

    # ---- main entry ----
    def handle(self, sock, conn_id: int, msg: Dict[str, Any]) -> None:
        action = msg.get("action")
        log(f"[conn {conn_id}] action={action} payload={msg}")
        if action == "register":
            self._handle_register(sock, msg)
        elif action == "login":
            self._handle_login(sock, conn_id, msg)
        else:
            # Require login for everything else
            sess = self.auth.require_login(conn_id)
            if not sess:
                send_error(sock, "Not logged in")
                return
            role = sess["role"]
            username = sess["username"]
            # dispatch by action
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
        send_json(sock, resp)

    def _handle_login(self, sock, conn_id: int, msg: Dict[str, Any]) -> None:
        username = msg.get("username", "").strip()
        password = msg.get("password", "")
        role = msg.get("role", "")
        resp = self.auth.login(conn_id, username, password, role)
        send_json(sock, resp)

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
        upload_id, chunk_size, _target = self.games.start_upload(
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
        if not game_id or rating < 1 or rating > 5:
            send_error(sock, "Invalid review")
            return
        ok = self.games.add_review(game_id, username, rating, comment)
        if not ok:
            send_error(sock, "Game not found")
        else:
            send_ok(sock)

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
        # Enforce version check: player must own latest version
        game = self.games.get_game(game_id)
        if not game:
            send_error(sock, "Game not found")
            return
        # 在這裡可以擴充：檢查使用者 `owned_games` 中的版本是否是最新；
        # 目前簡化：只檢查是否擁有該 game_id
        user = self.datastore.get_user(username)
        owned = (user or {}).get("owned_games", [])
        if game_id not in owned:
            send_error(sock, "You must download latest version before creating room")
            return

        game_port = self.games.allocate_game_port()
        resp = self.lobby.create_room(
            host_username=username,
            game_id=game_id,
            room_name=room_name,
            max_players=max_players,
            game_port=game_port,
        )
        send_json(sock, resp)

    def _handle_join_room(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return
        room = self.datastore.get_room(room_id)
        if not room:
            send_error(sock, "Room not found")
            return
        # Enforce version check: player must own latest version
        game_id = room["game_id"]
        game = self.games.get_game(game_id)
        if not game:
            send_error(sock, "Game not found")
            return
        user = self.datastore.get_user(username)
        owned = (user or {}).get("owned_games", [])
        if game_id not in owned:
            send_error(sock, "You must download latest version before joining room")
            return

        resp = self.lobby.join_room(room_id, username)
        send_json(sock, resp)

    def _handle_leave_room(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return
        resp = self.lobby.leave_room(room_id, username)
        send_json(sock, resp)

    def _handle_start_game(self, sock, username: str, msg: Dict[str, Any]) -> None:
        room_id = msg.get("room_id")
        if not room_id:
            send_error(sock, "room_id required")
            return
        room = self.datastore.get_room(room_id)
        if not room:
            send_error(sock, "Room not found")
            return
        if room["host"] != username:
            send_error(sock, "Only host can start the game")
            return
        resp = self.lobby.start_game(room_id)
        send_json(sock, resp)

    # ---- download ----
    def _handle_download_game(self, sock, username: str, msg: Dict[str, Any]) -> None:
        """這裡先只標記下載成功並更新 owned_games，真正檔案下載交給 Developer/Player 實作 zip 傳輸。"""
        game_id = msg.get("game_id")
        if not game_id:
            send_error(sock, "game_id required")
            return
        game = self.games.get_game(game_id)
        if not game:
            send_error(sock, "Game not found")
            return
        self.datastore.increment_download(username, game_id)
        # 先回傳遊戲的 file_path，讓 client 自己去開新連線下載或透過 developer_client 的傳輸協議下載
        send_ok(sock, file_path=game["file_path"])
