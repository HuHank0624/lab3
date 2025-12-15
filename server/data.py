# path: server/data.py
import json
import os
import threading
import uuid
import hashlib
from typing import Dict, Any, List, Optional

from .utils import *


USERS_PATH = os.path.join(DB_DIR, "users.json")
GAMES_PATH = os.path.join(DB_DIR, "games.json")
ROOMS_PATH = os.path.join(DB_DIR, "rooms.json")


def _ensure_file(path: str, default: Dict[str, Any]) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)


class JsonTable:
    """Small JSON 'table' with in-memory cache and mutex."""

    def __init__(self, path: str, default_root: Dict[str, Any]):
        self.path = path
        self.default_root = default_root
        self._lock = threading.RLock()  # Use RLock to allow reentrant locking
        _ensure_file(path, default_root)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # fallback to default if corrupted
                log("WARN: JSON corrupted at", self.path, "resetting to default_root")
                return self.default_root.copy()

    def _save_atomic(self) -> None:
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)

    def with_lock(self):
        return self._lock

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def save(self) -> None:
        with self._lock:
            self._save_atomic()


class DataStore:
    """High level API over users/games/rooms JSON 'DB'."""

    def __init__(self):
        self.users = JsonTable(USERS_PATH, {"users": []})
        self.games = JsonTable(GAMES_PATH, {"games": []})
        self.rooms = JsonTable(ROOMS_PATH, {"rooms": []})

    # ----- helpers -----
    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    # ----- Users -----
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self.users.with_lock():
            for u in self.users.data["users"]:
                if u["username"] == username:
                    return u
        return None

    def register_user(self, username: str, password: str, role: str) -> bool:
        with self.users.with_lock():
            users = self.users.data["users"]
            if any(u["username"] == username for u in users):
                return False
            users.append(
                {
                    "username": username,
                    "password": self._hash_password(password),
                    "role": role,
                    "owned_games": [],
                    "uploaded_games": [] if role == "developer" else [],
                }
            )
            self.users.save()
        log(f"New user registered: {username} ({role})")
        return True

    def validate_login(self, username: str, password: str, role: str) -> bool:
        u = self.get_user(username)
        if not u:
            return False
        if u.get("role") != role:
            return False
        return u.get("password") == self._hash_password(password)

    # ----- Games -----
    def list_games(self) -> List[Dict[str, Any]]:
        with self.games.with_lock():
            return list(self.games.data["games"])

    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        with self.games.with_lock():
            for g in self.games.data["games"]:
                if g["game_id"] == game_id:
                    return g
        return None

    def add_or_update_game(
        self,
        developer: str,
        name: str,
        version: str,
        description: str,
        file_path: str,
        cli_entry: str,
        gui_entry: str,
        game_id: Optional[str] = None,
    ) -> str:
        """If game_id is None, create; else update existing."""
        with self.games.with_lock(), self.users.with_lock():
            games = self.games.data["games"]
            if game_id:
                game = next((g for g in games if g["game_id"] == game_id), None)
            else:
                game = None

            if game is None:
                game_id = uuid.uuid4().hex
                game = {
                    "game_id": game_id,
                    "name": name,
                    "developer": developer,
                    "version": version,
                    "description": description,
                    "file_path": file_path,
                    "cli_entry": cli_entry,
                    "gui_entry": gui_entry,
                    "downloads": 0,
                    "reviews": [],
                }
                games.append(game)
                # add to developer.uploaded_games
                for u in self.users.data["users"]:
                    if u["username"] == developer:
                        u.setdefault("uploaded_games", []).append(game_id)
                        break
            else:
                game.update(
                    {
                        "name": name,
                        "version": version,
                        "description": description,
                        "file_path": file_path,
                        "cli_entry": cli_entry,
                        "gui_entry": gui_entry,
                    }
                )
            self.games.save()
            self.users.save()
        log(f"Game saved: {name} ({game_id}) v{version}")
        return game_id

    def increment_download(self, username: str, game_id: str) -> None:
        with self.games.with_lock(), self.users.with_lock():
            for g in self.games.data["games"]:
                if g["game_id"] == game_id:
                    g["downloads"] = int(g.get("downloads", 0)) + 1
                    break
            for u in self.users.data["users"]:
                if u["username"] == username:
                    owned = u.setdefault("owned_games", [])
                    if game_id not in owned:
                        owned.append(game_id)
                    break
            self.games.save()
            self.users.save()

    def add_review(self, game_id: str, username: str, rating: int, comment: str) -> bool:
        with self.games.with_lock():
            game = next((g for g in self.games.data["games"] if g["game_id"] == game_id), None)
            if not game:
                return False
            game.setdefault("reviews", []).append(
                {"username": username, "rating": rating, "comment": comment}
            )
            self.games.save()
        return True

    def delete_game(self, game_id: str) -> bool:
        """Delete a game from the database and remove from developer's uploaded_games."""
        with self.games.with_lock(), self.users.with_lock():
            games = self.games.data["games"]
            game = next((g for g in games if g["game_id"] == game_id), None)
            if not game:
                return False
            
            # Remove from games list
            games.remove(game)
            
            # Remove from developer's uploaded_games
            developer = game.get("developer")
            if developer:
                for u in self.users.data["users"]:
                    if u["username"] == developer:
                        uploaded = u.get("uploaded_games", [])
                        if game_id in uploaded:
                            uploaded.remove(game_id)
                        break
            
            self.games.save()
            self.users.save()
        return True

    # ----- Rooms -----
    def list_rooms(self) -> List[Dict[str, Any]]:
        with self.rooms.with_lock():
            return list(self.rooms.data["rooms"])

    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["room_id"] == room_id:
                    return r
        return None

    def get_room_by_host(self, host: str) -> Optional[Dict[str, Any]]:
        """Get room where user is the host."""
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["host"] == host:
                    return r
        return None

    def create_room(
        self,
        room_name: str,
        host: str,
        game_id: str,
        max_players: int,
        game_port: int,
    ) -> str:
        room_id = uuid.uuid4().hex[:8]
        with self.rooms.with_lock():
            self.rooms.data["rooms"].append(
                {
                    "room_id": room_id,
                    "room_name": room_name,
                    "host": host,
                    "game_id": game_id,
                    "players": [host],
                    "ready_players": [],  # Track which players are ready
                    "max_players": max_players,
                    "status": "waiting",
                    "game_port": game_port,
                }
            )
            self.rooms.save()
        log(f"Room created: {room_id} {room_name} game={game_id} host={host} port={game_port}")
        return room_id

    def join_room(self, room_id: str, username: str) -> bool:
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["room_id"] == room_id:
                    players = r.setdefault("players", [])
                    if username in players:
                        return True
                    if len(players) >= r["max_players"]:
                        return False
                    players.append(username)
                    self.rooms.save()
                    return True
        return False

    def leave_room(self, room_id: str, username: str) -> None:
        with self.rooms.with_lock():
            rooms = self.rooms.data["rooms"]
            for r in rooms[:]:
                if r["room_id"] == room_id:
                    players = r.setdefault("players", [])
                    if username in players:
                        players.remove(username)
                    # Also remove from ready list
                    ready = r.setdefault("ready_players", [])
                    if username in ready:
                        ready.remove(username)
                    # destroy room if empty
                    if not players:
                        rooms.remove(r)
                    self.rooms.save()
                    return

    def set_player_ready(self, room_id: str, username: str, ready: bool) -> bool:
        """Set a player's ready status. Returns True if successful."""
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["room_id"] == room_id:
                    players = r.get("players", [])
                    if username not in players:
                        return False
                    ready_list = r.setdefault("ready_players", [])
                    if ready:
                        if username not in ready_list:
                            ready_list.append(username)
                    else:
                        if username in ready_list:
                            ready_list.remove(username)
                    self.rooms.save()
                    return True
        return False

    def are_all_players_ready(self, room_id: str) -> bool:
        """Check if all players in room are ready."""
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["room_id"] == room_id:
                    players = r.get("players", [])
                    ready_list = r.get("ready_players", [])
                    # All players (except host can start without being ready)
                    # Actually let's require everyone to be ready
                    return len(players) > 1 and set(players) == set(ready_list)
        return False

    def delete_room(self, room_id: str) -> None:
        """Forcefully delete a room."""
        with self.rooms.with_lock():
            rooms = self.rooms.data["rooms"]
            for r in rooms[:]:
                if r["room_id"] == room_id:
                    rooms.remove(r)
                    self.rooms.save()
                    return

    def update_room_status(self, room_id: str, status: str) -> None:
        with self.rooms.with_lock():
            for r in self.rooms.data["rooms"]:
                if r["room_id"] == room_id:
                    r["status"] = status
                    self.rooms.save()
                    return
