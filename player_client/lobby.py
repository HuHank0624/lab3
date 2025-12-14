# path: player_client/lobby.py
import socket
from typing import Dict, Any, List, Optional
from utils.protocol import send_json, recv_json
from .library import GameLibrary
import subprocess
import os
import sys
from .utils import GAMES_ROOT


class LobbyClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username
        self.library = GameLibrary(username)
        self.current_room_id: Optional[str] = None

    # ----- helper -----

    def _fetch_rooms(self) -> List[Dict[str, Any]]:
        send_json(self.sock, {"action": "list_rooms"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ 無法取得房間列表:", resp)
            return []
        return resp.get("rooms", [])

    def _fetch_games(self) -> List[Dict[str, Any]]:
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ 無法取得遊戲列表:", resp)
            return []
        return resp.get("games", [])

    def _choose_game(self) -> Optional[Dict[str, Any]]:
        """Show all games and let user choose one."""
        games = self._fetch_games()
        if not games:
            print("⚠ No games available in store.")
            return None

        print("\n=== Select a Game ===")
        for idx, g in enumerate(games, start=1):
            print(f"{idx}. {g['name']} (id={g['game_id'][:8]}...) v{g['version']}")

        choice = input("Select game (or 0 to cancel): ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(games):
            return games[idx - 1]
        return None

    def _is_game_installed(self, game_id: str) -> bool:
        """Check if game is installed locally."""
        for d in GAMES_ROOT.iterdir():
            if d.name.startswith(game_id):
                return True
        return False

    def _get_game_dir(self, game_id: str) -> Optional[str]:
        """Get game directory if installed."""
        for d in GAMES_ROOT.iterdir():
            if d.name.startswith(game_id):
                return str(d)
        return None

    # ----- main lobby flow -----

    def lobby_menu(self) -> None:
        while True:
            print("\n=== Game Lobby ===")
            print("1. View room list")
            print("2. Create new room")
            print("3. Join room")
            print("4. Leave room")
            print("5. Start game (host only)")
            print("0. Back to main menu")
            choice = input("> ").strip()

            if choice == "0":
                return
            elif choice == "1":
                self.show_rooms()
            elif choice == "2":
                self.create_room()
            elif choice == "3":
                self.join_room()
            elif choice == "4":
                self.leave_room()
            elif choice == "5":
                self.start_game()
            else:
                print("無效選項。")

    def show_rooms(self) -> None:
        rooms = self._fetch_rooms()
        print("\n=== Room List ===")
        if not rooms:
            print("(No rooms available)")
            return
        for r in rooms:
            players = ", ".join(r.get("players", []))
            status = "waiting" if r['status'] == "waiting" else "in-game"
            print(
                f"  [{r['room_id']}] {r['room_name']}\n"
                f"    Game: {r['game_id'][:8]}... | Host: {r['host']}\n"
                f"    Players ({len(r.get('players', []))}/{r['max_players']}): {players}\n"
                f"    Status: {status}"
            )

    def create_room(self) -> None:
        game = self._choose_game()
        if not game:
            return

        # Check if game is installed
        if not self._is_game_installed(game["game_id"]):
            print(f"⚠ Game not downloaded. Please download '{game['name']}' from the store first.")
            return

        room_name = input("Room name: ").strip() or "Room"
        max_players_str = input("Max players (default 2): ").strip()
        max_players = int(max_players_str) if max_players_str.isdigit() else 2

        send_json(self.sock, {
            "action": "create_room",
            "game_id": game["game_id"],
            "room_name": room_name,
            "max_players": max_players,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            self.current_room_id = resp.get("room_id")
            print(f"✅ Room created! Room ID: {self.current_room_id}")
            print(f"   Game port: {resp.get('game_port')}")
        else:
            print(f"❌ Failed to create room: {resp.get('message', 'Unknown error')}")

    def join_room(self) -> None:
        self.show_rooms()
        room_id = input("\nEnter room_id to join: ").strip()
        if not room_id:
            return

        send_json(self.sock, {
            "action": "join_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            self.current_room_id = room_id
            room_info = resp.get("room_info", {})
            game_id = room_info.get("game_id")
            print(f"✅ Successfully joined room {room_id}")
            
            # Check if game is installed
            if game_id and not self._is_game_installed(game_id):
                print(f"⚠ Note: Game not downloaded yet. Please download before game starts.")
        else:
            print(f"❌ Failed to join: {resp.get('message', 'Unknown error')}")

    def leave_room(self) -> None:
        if self.current_room_id:
            room_id = self.current_room_id
        else:
            room_id = input("Enter room_id to leave: ").strip()
        
        if not room_id:
            return

        send_json(self.sock, {
            "action": "leave_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            print(f"✅ Left room {room_id}")
            if self.current_room_id == room_id:
                self.current_room_id = None
        else:
            print(f"❌ Failed to leave: {resp.get('message', 'Unknown error')}")

    def start_game(self) -> None:
        if self.current_room_id:
            room_id = self.current_room_id
            print(f"Using current room: {room_id}")
        else:
            room_id = input("Enter room_id to start: ").strip()

        if not room_id:
            return

        send_json(self.sock, {"action": "start_game", "room_id": room_id})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print(f"❌ Failed to start: {resp.get('message', 'Unknown error')}")
            return

        room_info = resp.get("room_info", {})
        game_port = resp.get("game_port")
        game_id = room_info.get("game_id")

        print(f"✅ Game starting on port {game_port}")

        # Find local game directory
        game_dir = self._get_game_dir(game_id)
        if not game_dir:
            print("⚠ Game not downloaded, cannot launch client")
            return

        # Find client entry
        entry = None
        for root, dirs, files in os.walk(game_dir):
            for f in files:
                if "client" in f.lower() and f.endswith(".py"):
                    entry = os.path.join(root, f)
                    break
            if entry:
                break

        if not entry:
            print("⚠ Cannot find client entry file")
            return

        # Launch game client
        cmd = [
            sys.executable, entry,
            "--host", "127.0.0.1",
            "--port", str(game_port),
            "--name", self.username
        ]
        print(f"🎮 Launching game: {' '.join(cmd)}")
        
        try:
            subprocess.Popen(cmd)
            print("✅ Game launched!")
        except Exception as e:
            print(f"❌ Launch failed: {e}")

