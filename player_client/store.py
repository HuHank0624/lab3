import socket
import zipfile
from typing import List, Dict, Any, Optional

from utils.protocol import send_json, recv_json
from utils.file_transfer import decode_chunk
from .utils import DOWNLOAD_ROOT, GAMES_ROOT
import os

class GameStoreClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

        # single source of truth
        self.games: List[Dict[str, Any]] = []

    # -----------------------------
    # Server interaction
    # -----------------------------

    def refresh_games(self) -> None:
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ Failed to fetch game list:", resp.get("message", "Unknown error"))
            self.games = []
            return
        self.games = resp.get("games", [])

    # -----------------------------
    # UI helpers
    # -----------------------------

    def show_game_list(self) -> None:
        print("\n=== Game Store ===")
        if not self.games:
            print("(No games available)")
            return
        for idx, g in enumerate(self.games, start=1):
            avg_rating = self._calc_avg_rating(g)
            rating_str = f"★{avg_rating:.1f}" if avg_rating else "No ratings"
            print(
                f"{idx}. {g['name']} (id={g['game_id'][:8]}...) "
                f"by {g['developer']} v{g['version']} [{rating_str}]"
            )

    def _calc_avg_rating(self, game: Dict[str, Any]) -> Optional[float]:
        reviews = game.get("reviews", [])
        if not reviews:
            return None
        total = sum(r.get("rating", 0) for r in reviews)
        return total / len(reviews)

    def select_game(self) -> Optional[Dict[str, Any]]:
        if not self.games:
            return None
        choice = input("Enter game number (or 0 to go back): ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(self.games):
            return self.games[idx - 1]
        return None

    def show_game_detail(self, game: Dict[str, Any]) -> None:
        print(f"\n=== Game Details: {game['name']} ===")
        print(f"ID: {game['game_id']}")
        print(f"Developer: {game['developer']}")
        print(f"Version: {game['version']}")
        print(f"Description: {game.get('description', '(No description)')}")
        print(f"Downloads: {game.get('downloads', 0)}")
        
        reviews = game.get("reviews", [])
        avg_rating = self._calc_avg_rating(game)
        if avg_rating:
            print(f"Rating: ★{avg_rating:.1f} ({len(reviews)} reviews)")
        else:
            print("Rating: No ratings yet")
        
        if reviews:
            print("\n--- Player Reviews ---")
            for r in reviews[-5:]:  # Show last 5 reviews
                print(f"  {r['username']}: ★{r['rating']} - {r.get('comment', '')}")

    # -----------------------------
    # Main store flow
    # -----------------------------

    def view_store(self) -> None:
        self.refresh_games()

        while True:
            self.show_game_list()
            print("\nOptions:")
            print("a. Refresh list")
            print("v. View game details")
            print("d. Download game")
            print("0. Back to main menu")
            choice = input("> ").strip().lower()

            if choice == "0":
                return

            elif choice == "a":
                self.refresh_games()

            elif choice == "v":
                game = self.select_game()
                if game:
                    self.show_game_detail(game)
                    input("Press Enter to continue...")

            elif choice == "d":
                game = self.select_game()
                if not game:
                    continue

                self._download_game(game)

            else:
                print("Invalid option.")

    def _download_game(self, game: Dict[str, Any]) -> bool:
        """Download game from server via chunk protocol."""
        game_id = game["game_id"]
        name = game["name"]
        version = game.get("version", "1")
        
        print(f"\nDownloading game: {name} v{version}...")

        send_json(self.sock, {
            "action": "download_game",
            "game_id": game_id,
        })

        # Create directory for download (per-user)
        user_download_dir = os.path.join(DOWNLOAD_ROOT, self.username)
        os.makedirs(user_download_dir, exist_ok=True)
        zip_path = os.path.join(user_download_dir, f"{name}.zip")

        try:
            with open(zip_path, "wb") as f:
                while True:
                    msg = recv_json(self.sock)
                    if not msg:
                        print("Connection lost")
                        return False

                    # Check for error response
                    if msg.get("status") == "error":
                        print(f"Download failed: {msg.get('message', 'Unknown error')}")
                        return False

                    if msg.get("action") != "download_chunk":
                        print(f"Unexpected response: {msg.get('message', msg)}")
                        return False

                    if msg.get("eof"):
                        break

                    data = msg.get("data")
                    if data:
                        f.write(decode_chunk(data))

            print(f"Download complete: {zip_path}")

            # Extract to per-user games directory using game name
            user_games_dir = os.path.join(GAMES_ROOT, self.username)
            os.makedirs(user_games_dir, exist_ok=True)
            
            # Use game name as folder name (with game_id prefix for uniqueness)
            game_folder_name = f"{name.replace(' ', '_')}"
            extract_path = os.path.join(user_games_dir, game_folder_name)
            
            # Remove old version if exists
            if os.path.exists(extract_path):
                import shutil
                shutil.rmtree(extract_path)
            
            os.makedirs(extract_path, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_path)
                
                # Save game info for version tracking
                info_path = os.path.join(extract_path, "game_info.json")
                with open(info_path, "w", encoding="utf-8") as f:
                    import json
                    json.dump({
                        "game_id": game_id,
                        "name": name,
                        "version": version,
                        "developer": game.get("developer", ""),
                    }, f, indent=2)
                
                print(f"Extracted to: {extract_path}")
            except zipfile.BadZipFile:
                print("Corrupted zip file")
                return False

            return True

        except Exception as e:
            print(f"Download error: {e}")
            return False
