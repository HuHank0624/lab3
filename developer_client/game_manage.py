# path: developer_client/game_manage.py
import socket
from typing import List, Dict, Any, Optional
from utils.protocol import send_json, recv_json


class GameManagerClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    def _fetch_my_games(self) -> List[Dict[str, Any]]:
        """Fetch list of games uploaded by current developer."""
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print("❌ Failed to fetch games:", resp)
            return []

        # Filter to only show games by this developer
        all_games = resp.get("games", [])
        return [g for g in all_games if g.get("developer") == self.username]

    def list_my_games(self) -> None:
        games = self._fetch_my_games()
        
        print("\n=== Your Uploaded Games ===")
        if not games:
            print("(No games uploaded yet)")
            return
        
        for idx, g in enumerate(games, start=1):
            downloads = g.get("downloads", 0)
            reviews = g.get("reviews", [])
            avg_rating = sum(r.get("rating", 0) for r in reviews) / len(reviews) if reviews else 0
            rating_str = f"★{avg_rating:.1f}" if reviews else "No ratings"
            
            print(f"{idx}. {g['name']} (id={g['game_id'][:8]}...)")
            print(f"   Version: {g['version']} | Downloads: {downloads} | Rating: {rating_str}")
            print(f"   Description: {g.get('description', '(none)')[:50]}")

    def select_my_game(self) -> Optional[Dict[str, Any]]:
        """Show game list and let developer select one."""
        games = self._fetch_my_games()
        
        if not games:
            print("(No games to select)")
            return None
        
        print("\n=== Select a Game ===")
        for idx, g in enumerate(games, start=1):
            print(f"{idx}. {g['name']} (v{g['version']}) - id={g['game_id'][:8]}...")
        
        choice = input("Enter game number (or 0 to cancel): ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(games):
            return games[idx - 1]
        return None

    def update_game(self) -> None:
        print("\n=== Update Game ===")
        game = self.select_my_game()
        if not game:
            return
        
        print(f"\nUpdating: {game['name']} (current version: {game['version']})")
        print("Note: To update, you'll re-upload the game files.")
        print("The game ID will remain the same, but version should be incremented.")
        
        # Use uploader for actual upload
        from .game_upload import GameUploader
        uploader = GameUploader(self.sock, self.username)
        uploader.upload_game()

    def delete_game(self) -> None:
        print("\n=== Delete (Unlist) Game ===")
        game = self.select_my_game()
        if not game:
            return
        
        print(f"\n⚠️  You are about to delete: {game['name']} (id={game['game_id'][:8]}...)")
        print("This will remove the game from the store.")
        confirm = input("Type 'DELETE' to confirm: ").strip()
        
        if confirm != "DELETE":
            print("Cancelled.")
            return
        
        send_json(self.sock, {
            "action": "delete_game",
            "game_id": game["game_id"],
        })
        resp = recv_json(self.sock)
        
        if resp and resp.get("status") == "ok":
            print(f"✅ Game deleted successfully!")
        else:
            print(f"❌ Delete failed: {resp}")
