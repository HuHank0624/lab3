# path: player_client/lobby.py
import socket
from typing import Dict, Any, List, Optional
from utils.protocol import send_json, recv_json
from .library import GameLibrary
import subprocess
import os
import sys
from .utils import GAMES_ROOT

# Import server host from config for game client connection
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import SERVER_HOST
except ImportError:
    SERVER_HOST = "127.0.0.1"


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
            print("[!] Failed to fetch room list")
            return []
        return resp.get("rooms", [])

    def _fetch_games(self) -> List[Dict[str, Any]]:
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("[!] Failed to fetch game list")
            return []
        return resp.get("games", [])

    def _choose_game(self) -> Optional[Dict[str, Any]]:
        """Show all games and let user choose one."""
        games = self._fetch_games()
        if not games:
            print("[!] No games available in store.")
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
        """Check if game is installed locally for this user."""
        user_games_dir = GAMES_ROOT / self.username
        if not user_games_dir.exists():
            return False
        for d in user_games_dir.iterdir():
            info_file = d / "game_info.json"
            if info_file.exists():
                try:
                    import json
                    with open(info_file, "r") as f:
                        info = json.load(f)
                        if info.get("game_id") == game_id:
                            return True
                except:
                    pass
        return False

    def _get_game_dir(self, game_id: str) -> Optional[str]:
        """Get game directory if installed for this user."""
        user_games_dir = GAMES_ROOT / self.username
        if not user_games_dir.exists():
            return None
        for d in user_games_dir.iterdir():
            info_file = d / "game_info.json"
            if info_file.exists():
                try:
                    import json
                    with open(info_file, "r") as f:
                        info = json.load(f)
                        if info.get("game_id") == game_id:
                            return str(d)
                except:
                    pass
        return None

    # ----- main lobby flow -----

    def lobby_menu(self) -> None:
        page = 1
        while True:
            if page == 1:
                print("\n=== Game Lobby (Page 1/2) ===")
                print("1. View room list")
                print("2. Create new room")
                print("3. Join room")
                print("4. Leave room")
                print("n. Next page ->")
                print("0. Back to main menu")
                choice = input("> ").strip().lower()

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
                elif choice == "n":
                    page = 2
                else:
                    print("Invalid option.")
            else:  # page == 2
                print("\n=== Game Lobby (Page 2/2) ===")
                print("5. Start game (host only)")
                print("6. Launch game client (after host starts)")
                print("7. Close room (host only)")
                print("p. <- Previous page")
                print("0. Back to main menu")
                choice = input("> ").strip().lower()

                if choice == "0":
                    return
                elif choice == "5":
                    self.start_game()
                elif choice == "6":
                    self.launch_game_client()
                elif choice == "7":
                    self.close_room()
                elif choice == "p":
                    page = 1
                else:
                    print("Invalid option.")

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
                f"\n  Room ID: {r['room_id']}\n"
                f"  Name: {r['room_name']}\n"
                f"  Game: {r['game_id'][:8]}... | Host: {r['host']}\n"
                f"  Players ({len(r.get('players', []))}/{r['max_players']}): {players}\n"
                f"  Status: {status} | Port: {r.get('game_port', 'N/A')}"
            )
        print()

    def create_room(self) -> None:
        game = self._choose_game()
        if not game:
            return

        # Check if game is installed
        if not self._is_game_installed(game["game_id"]):
            print(f"[!] Game not downloaded. Please download '{game['name']}' from the store first.")
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
            print(f"[OK] Room created! Room ID: {self.current_room_id}")
            print(f"     Game port: {resp.get('game_port')}")
        else:
            print(f"[!] Failed to create room: {resp.get('message', 'Unknown error')}")

    def join_room(self) -> None:
        # Check if already in a room
        if self.current_room_id:
            print(f"[!] You are already in room {self.current_room_id}")
            print("    Please leave current room first (option 4).")
            return

        self.show_rooms()
        room_id = input("\nEnter room_id to join: ").strip()
        if not room_id:
            return

        # First, get room info to check the game_id
        send_json(self.sock, {"action": "get_room_info", "room_id": room_id})
        info_resp = recv_json(self.sock)
        
        if not info_resp or info_resp.get("status") != "ok":
            print(f"[!] Room not found: {room_id}")
            return
        
        room_info = info_resp.get("room", {})
        game_id = room_info.get("game_id")
        
        # Check if game is installed BEFORE joining
        if game_id and not self._is_game_installed(game_id):
            print(f"[!] You haven't downloaded this game yet.")
            print(f"    Please download it from the Game Store first.")
            return

        # Now actually join the room
        send_json(self.sock, {
            "action": "join_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            self.current_room_id = room_id
            print(f"[OK] Successfully joined room {room_id}")
        else:
            print(f"[!] Failed to join: {resp.get('message', 'Unknown error')}")

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
            print(f"[OK] Left room {room_id}")
            if self.current_room_id == room_id:
                self.current_room_id = None
        else:
            print(f"[!] Failed to leave: {resp.get('message', 'Unknown error')}")

    def close_room(self) -> None:
        """Close/delete a room (host only). Useful when game ends or has issues."""
        if self.current_room_id:
            room_id = self.current_room_id
            print(f"Using current room: {room_id}")
        else:
            room_id = input("Enter room_id to close: ").strip()

        if not room_id:
            return

        send_json(self.sock, {"action": "close_room", "room_id": room_id})
        resp = recv_json(self.sock)

        if resp and resp.get("status") == "ok":
            print(f"[OK] Room {room_id} closed.")
            if self.current_room_id == room_id:
                self.current_room_id = None
        else:
            print(f"[!] Failed to close: {resp.get('message', 'Unknown error')}")

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
            print(f"[!] Failed to start: {resp.get('message', 'Unknown error')}")
            return

        room_info = resp.get("room_info", {})
        game_port = resp.get("game_port")

        print(f"[OK] Game server started on port {game_port}")
        print(f"    All players in the room can now use option 6 to launch the game client.")

    def launch_game_client(self) -> None:
        """Launch game client to connect to the game server. Used by ALL players after host starts the game."""
        if self.current_room_id:
            room_id = self.current_room_id
            print(f"Using current room: {room_id}")
        else:
            room_id = input("Enter room_id: ").strip()

        if not room_id:
            return

        # Get room info to check status and get port
        send_json(self.sock, {"action": "get_room_info", "room_id": room_id})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print(f"[!] Failed: {resp.get('message', 'Unknown error')}")
            return

        room_info = resp.get("room")
        if not room_info:
            print("[!] Room info not found")
            return

        if room_info.get("status") != "playing":
            print(f"[!] Game not started yet. Status: {room_info.get('status')}")
            print("    Wait for the host to start the game, then try again.")
            return

        game_port = room_info.get("game_port")
        game_id = room_info.get("game_id")

        print(f"[OK] Game is running on port {game_port}")

        # Find local game directory
        game_dir = self._get_game_dir(game_id)
        if not game_dir:
            print("[!] Game not downloaded, cannot launch client")
            return

        # Find client entry - prefer GUI client if available
        gui_entry = None
        cli_entry = None
        
        for root, dirs, files in os.walk(game_dir):
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    if "client" in f.lower() and "gui" in f.lower():
                        gui_entry = fpath
                    elif "client" in f.lower():
                        cli_entry = fpath
        
        entry = gui_entry or cli_entry

        if not entry:
            print("[!] Cannot find client entry file")
            return

        client_type = "GUI" if gui_entry else "CLI"
        print(f"[*] Using {client_type} client: {os.path.basename(entry)}")

        # Launch game client - use SERVER_HOST from config
        cmd = [
            sys.executable, entry,
            "--host", SERVER_HOST,
            "--port", str(game_port),
            "--name", self.username
        ]
        print(f"[*] Launching game: {' '.join(cmd)}")
        
        try:
            subprocess.Popen(cmd)
            print("[OK] Game launched!")
        except Exception as e:
            print(f"[!] Launch failed: {e}")
