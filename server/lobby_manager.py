# path: server/lobby_manager.py
from typing import Dict, Any, List, Optional

from .data import DataStore
from .utils import log
# server/lobby_manager.py
from .game_runtime import GameRuntime


class LobbyManager:
    """Room list / matchmaking view over DataStore."""

    def __init__(self, datastore: DataStore):
        self.datastore = datastore
        self.runtime = GameRuntime()

        # For potential future: mapping room_id -> game server process/port etc.

    def list_rooms(self) -> List[Dict[str, Any]]:
        return self.datastore.list_rooms()

    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        return self.datastore.get_room(room_id)

    def create_room(
        self,
        host_username: str,
        game_id: str,
        room_name: str,
        max_players: int,
        game_port: int,
    ) -> Dict[str, Any]:
        room_id = self.datastore.create_room(
            room_name=room_name,
            host=host_username,
            game_id=game_id,
            max_players=max_players,
            game_port=game_port,
        )
        return {
            "status": "ok",
            "room_id": room_id,
            "game_port": game_port,
        }

    def join_room(self, room_id: str, username: str) -> Dict[str, Any]:
        room = self.datastore.get_room(room_id)
        if not room:
            return {"status": "error", "message": "Room not found"}
        if room["status"] != "waiting":
            return {"status": "error", "message": "Room already started"}
        if not self.datastore.join_room(room_id, username):
            return {"status": "error", "message": "Room is full"}
        room = self.datastore.get_room(room_id)  # refetch
        return {"status": "ok", "room_info": room}

    def leave_room(self, room_id: str, username: str) -> Dict[str, Any]:
        self.datastore.leave_room(room_id, username)
        return {"status": "ok"}

    def close_room(self, room_id: str) -> Dict[str, Any]:
        """Close/delete a room and stop any running game server."""
        room = self.datastore.get_room(room_id)
        if not room:
            return {"status": "error", "message": "Room not found"}

        # Stop game server if running
        if room_id in self.runtime.running_servers:
            proc = self.runtime.running_servers[room_id]
            try:
                proc.terminate()
            except:
                pass
            del self.runtime.running_servers[room_id]

        # Delete room from database
        self.datastore.delete_room(room_id)
        return {"status": "ok"}

    def start_game(self, room_id: str, username: str) -> Dict[str, Any]:
        room = self.datastore.get_room(room_id)
        if not room:
            return {"status": "error", "message": "Room not found"}
        if room["status"] != "waiting":
            return {"status": "error", "message": "Game already started"}
        if room.get("host") != username:
            return {"status": "error", "message": "Only the host can start the game"}

        # Check if all players are ready
        players = room.get("players", [])
        ready_players = room.get("ready_players", [])
        
        if len(players) < 2:
            return {"status": "error", "message": "Need at least 2 players to start"}
        
        # All players must be ready
        if set(players) != set(ready_players):
            not_ready = [p for p in players if p not in ready_players]
            return {"status": "error", "message": f"Not all players are ready. Waiting for: {', '.join(not_ready)}"}

        game = self.datastore.get_game(room["game_id"])
        if not game:
            return {"status": "error", "message": "Game not found"}

        port = room["game_port"]

        # Start game server
        ok = self.runtime.start_game_server(room_id, game, port)
        if not ok:
            return {"status": "error", "message": "Failed to launch game server"}

        self.datastore.update_room_status(room_id, "playing")
        return {
            "status": "ok",
            "room_info": self.datastore.get_room(room_id),
            "game_port": port,
        }
