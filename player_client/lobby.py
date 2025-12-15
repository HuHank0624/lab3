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
            max_p = g.get('max_players', 2)
            print(f"{idx}. {g['name']} (v{g['version']}) [{max_p} players]")

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

    def _get_installed_game_version(self, game_id: str) -> Optional[str]:
        """Get version of installed game."""
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
                            return info.get("version")
                except:
                    pass
        return None

    # ----- main lobby flow -----

    def lobby_menu(self) -> None:
        while True:
            print("\n=== Game Lobby ===")
            print("1. View room list")
            print("2. Create new room")
            print("3. Join room")
            print("4. Leave room")
            print("5. Ready / Unready")
            print("6. Start game (host only, auto-launches for all)")
            print("7. Launch game client (if not auto-launched)")
            print("8. Close room (host only)")
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
                self.toggle_ready()
            elif choice == "6":
                self.start_game()
            elif choice == "7":
                self.launch_game_client()
            elif choice == "8":
                self.close_room()
            else:
                print("Invalid option.")

    def show_rooms(self) -> None:
        rooms = self._fetch_rooms()
        print("\n=== Room List ===")
        if not rooms:
            print("(No rooms available)")
            return
        for r in rooms:
            players = r.get("players", [])
            ready_players = r.get("ready_players", [])
            # Format players with ready status
            player_list = []
            for p in players:
                if p in ready_players:
                    player_list.append(f"{p} [Ready]")
                else:
                    player_list.append(f"{p}")
            players_str = ", ".join(player_list)
            
            status = "waiting" if r['status'] == "waiting" else "in-game"
            ready_count = len(ready_players)
            total_count = len(players)
            
            print(
                f"\n  Room ID: {r['room_id']}\n"
                f"  Name: {r['room_name']}\n"
                f"  Game: {r['game_id'][:8]}... | Host: {r['host']}\n"
                f"  Players ({total_count}/{r['max_players']}): {players_str}\n"
                f"  Ready: {ready_count}/{total_count} | Status: {status} | Port: {r.get('game_port', 'N/A')}"
            )
        print()

    def toggle_ready(self) -> None:
        """Toggle ready status for current room."""
        if not self.current_room_id:
            print("[!] You are not in a room. Join a room first.")
            return

        # Get current room info to check ready status
        send_json(self.sock, {"action": "get_room_info", "room_id": self.current_room_id})
        resp = recv_json(self.sock)
        
        if resp.get("status") != "ok":
            print(f"[!] Failed to get room info: {resp.get('message', 'Unknown error')}")
            return

        room = resp.get("room", {})
        ready_players = room.get("ready_players", [])
        
        # Toggle: determine new state and use set_ready
        new_ready = self.username not in ready_players
        send_json(self.sock, {"action": "set_ready", "room_id": self.current_room_id, "ready": new_ready})
        resp = recv_json(self.sock)
        if resp.get("status") == "ok":
            if new_ready:
                print("[OK] You are now READY!")
            else:
                print("[OK] You are now NOT READY")
        else:
            print(f"[!] Failed: {resp.get('message', 'Unknown error')}")

    def waiting_room(self) -> None:
        """Enter the waiting room - shows room status, allows ready toggle, and auto-launches when game starts."""
        if not self.current_room_id:
            print("[!] You are not in a room. Join a room first.")
            return

        print("\n=== Waiting Room ===")
        print("Commands: 'r' = toggle ready, 's' = start game (host only), 'q' = quit waiting room, '' (enter) = refresh")
        print("The game client will auto-launch when the host starts the game!\n")

        while True:
            # Get current room info
            send_json(self.sock, {"action": "get_room_info", "room_id": self.current_room_id})
            resp = recv_json(self.sock)
            
            if resp.get("status") != "ok":
                print(f"[!] Failed to get room info: {resp.get('message', 'Unknown error')}")
                return

            room = resp.get("room", {})
            
            # Check if room still exists
            if not room:
                print("[!] Room no longer exists.")
                self.current_room_id = None
                return
            
            # Check if game has started - auto-launch!
            if room.get("status") == "playing":
                print("\n[!] Game has started! Launching game client...")
                self._auto_launch_game(room)
                return

            # Display room status
            players = room.get("players", [])
            ready_players = room.get("ready_players", [])
            is_host = room.get("host") == self.username
            my_ready = self.username in ready_players
            
            print(f"--- Room: {room.get('room_name', 'Unknown')} ---")
            print(f"Game: {room.get('game_id', 'Unknown')[:8]}...")
            print(f"Players ({len(players)}/{room.get('max_players', 2)}):")
            for p in players:
                status = "[READY]" if p in ready_players else "[NOT READY]"
                host_tag = " (HOST)" if p == room.get("host") else ""
                you_tag = " <-- YOU" if p == self.username else ""
                print(f"  - {p} {status}{host_tag}{you_tag}")
            
            print(f"\nReady: {len(ready_players)}/{len(players)}")
            
            # Show available actions
            print(f"\n[r] Toggle Ready (currently: {'READY' if my_ready else 'NOT READY'})")
            if is_host:
                all_ready = len(ready_players) == len(players) and len(players) >= 2
                if all_ready:
                    print("[s] Start Game (all players ready!)")
                else:
                    print("[s] Start Game (waiting for all players to be ready)")
            print("[q] Quit waiting room")
            print("[Enter] Refresh status")
            
            user_input = input("\n> ").strip().lower()
            
            if user_input == 'q':
                print("[*] Leaving waiting room (you're still in the room)")
                return
            elif user_input == 'r':
                self._do_toggle_ready()
            elif user_input == 's':
                if is_host:
                    self._do_start_game()
                    # Check if game started successfully
                    send_json(self.sock, {"action": "get_room_info", "room_id": self.current_room_id})
                    check_resp = recv_json(self.sock)
                    if check_resp.get("status") == "ok":
                        check_room = check_resp.get("room", {})
                        if check_room.get("status") == "playing":
                            print("\n[!] Game started! Launching game client...")
                            self._auto_launch_game(check_room)
                            return
                else:
                    print("[!] Only the host can start the game.")
            # Empty input or anything else just refreshes
            
            print("\n" + "="*40 + "\n")

    def _do_toggle_ready(self) -> None:
        """Internal: toggle ready status without room check."""
        send_json(self.sock, {"action": "get_room_info", "room_id": self.current_room_id})
        resp = recv_json(self.sock)
        
        if resp.get("status") != "ok":
            print(f"[!] Failed to get room info: {resp.get('message', 'Unknown error')}")
            return

        room = resp.get("room", {})
        ready_players = room.get("ready_players", [])
        
        # Toggle
        new_ready = self.username not in ready_players
        send_json(self.sock, {"action": "set_ready", "room_id": self.current_room_id, "ready": new_ready})
        resp = recv_json(self.sock)
        if resp.get("status") == "ok":
            if new_ready:
                print("[OK] You are now READY!")
            else:
                print("[OK] You are now NOT READY")
        else:
            print(f"[!] Failed: {resp.get('message', 'Unknown error')}")

    def _do_start_game(self) -> None:
        """Internal: start game without prompts."""
        send_json(self.sock, {"action": "start_game", "room_id": self.current_room_id})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print(f"[!] Failed to start: {resp.get('message', 'Unknown error')}")
            return

        game_port = resp.get("game_port")
        print(f"[OK] Game server started on port {game_port}")

    def _auto_launch_game(self, room: Dict[str, Any]) -> None:
        """Auto-launch game client when game starts. Waits for game to finish, then returns to waiting room."""
        game_port = room.get("game_port")
        game_id = room.get("game_id")

        if not game_port:
            print("[!] Game port not available")
            return

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
            # Redirect stdout/stderr to DEVNULL so game output doesn't clutter the lobby terminal
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[OK] Game launched!")
            print("[*] Waiting for game to finish...")
            
            # Wait for game client to close
            proc.wait()
            
            print("\n[*] Game ended. Returning to waiting room...")
            
            # Notify server to reset room status
            if self.current_room_id:
                send_json(self.sock, {"action": "end_game", "room_id": self.current_room_id})
                resp = recv_json(self.sock)
                if resp and resp.get("status") == "ok":
                    print("[OK] Room reset to waiting state.")
                # Go back to waiting room loop
                self.waiting_room()
            
        except Exception as e:
            print(f"[!] Launch failed: {e}")

    def create_room(self) -> None:
        game = self._choose_game()
        if not game:
            return

        # Check if game is installed
        if not self._is_game_installed(game["game_id"]):
            print(f"[!] Game not downloaded. Please download '{game['name']}' from the store first.")
            return

        room_name = input("Room name: ").strip() or "Room"
        
        # Use max_players from game config
        max_players = game.get("max_players", 2)
        print(f"[*] This game supports up to {max_players} players.")

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
            print("[*] Entering waiting room...")
            self.waiting_room()  # Auto-enter waiting room after creating
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

        # Check version compatibility - get server's current game version
        send_json(self.sock, {"action": "get_game_info", "game_id": game_id})
        game_resp = recv_json(self.sock)
        if game_resp and game_resp.get("status") == "ok":
            server_game = game_resp.get("game", {})
            server_version = server_game.get("version")
            local_version = self._get_installed_game_version(game_id)
            
            if server_version and local_version and server_version != local_version:
                print(f"[!] Version mismatch!")
                print(f"    Your version: {local_version}")
                print(f"    Server version: {server_version}")
                print(f"    Please re-download the game to get the latest version.")
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
            print("[*] Entering waiting room...")
            self.waiting_room()  # Auto-enter waiting room after joining
        else:
            print(f"[!] Failed to join: {resp.get('message', 'Unknown error')}")

    def leave_room(self) -> None:
        if not self.current_room_id:
            print("[!] You are not in any room.")
            return

        room_id = self.current_room_id
        send_json(self.sock, {
            "action": "leave_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            print(f"[OK] Left room {room_id}")
            self.current_room_id = None
        else:
            print(f"[!] Failed to leave: {resp.get('message', 'Unknown error')}")

    def toggle_ready(self) -> None:
        """Toggle ready status in current room."""
        if not self.current_room_id:
            print("[!] You are not in any room.")
            return

        # Get current ready status from room info
        send_json(self.sock, {"action": "get_room_info", "room_id": self.current_room_id})
        resp = recv_json(self.sock)
        
        if resp.get("status") != "ok":
            print(f"[!] Failed to get room info: {resp.get('message', 'Unknown error')}")
            return
        
        room = resp.get("room", {})
        ready_players = room.get("ready_players", [])
        currently_ready = self.username in ready_players
        
        # Toggle: if ready -> unready, if not ready -> ready
        new_ready = not currently_ready
        
        send_json(self.sock, {
            "action": "set_ready",
            "room_id": self.current_room_id,
            "ready": new_ready,
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            if new_ready:
                print(f"[OK] You are now READY!")
            else:
                print(f"[OK] You are now NOT READY.")
        else:
            print(f"[!] Failed: {resp.get('message', 'Unknown error')}")

    def close_room(self) -> None:
        """Close/delete a room (host only)."""
        if not self.current_room_id:
            print("[!] You are not in any room.")
            return

        room_id = self.current_room_id
        send_json(self.sock, {"action": "close_room", "room_id": room_id})
        resp = recv_json(self.sock)

        if resp and resp.get("status") == "ok":
            print(f"[OK] Room {room_id} closed.")
            self.current_room_id = None
        else:
            print(f"[!] Failed to close: {resp.get('message', 'Unknown error')}")

    def start_game(self) -> None:
        if not self.current_room_id:
            print("[!] You are not in any room.")
            return

        room_id = self.current_room_id
        send_json(self.sock, {"action": "start_game", "room_id": room_id})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print(f"[!] Failed to start: {resp.get('message', 'Unknown error')}")
            return

        room_info = resp.get("room_info", {})
        game_port = resp.get("game_port")

        print(f"[OK] Game server started on port {game_port}")
        print(f"    Launching game client...")
        
        # Auto-launch game client for host
        self._auto_launch_game(room_info)

    def launch_game_client(self) -> None:
        """Launch game client to connect to the game server. Used by ALL players after host starts the game."""
        if not self.current_room_id:
            print("[!] You are not in any room.")
            return

        room_id = self.current_room_id

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
            # Redirect stdout/stderr to DEVNULL so game output doesn't clutter the lobby terminal
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[OK] Game launched!")
        except Exception as e:
            print(f"[!] Launch failed: {e}")
