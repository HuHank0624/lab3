# path: player_client/review.py
import socket
from typing import Dict, Any, List
from utils.protocol import send_json, recv_json


class ReviewClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    def submit_review(self, game: Dict[str, Any]) -> None:
        print("\n=== Rate & Review ===")
        print(f"Game: {game['name']} (id={game['game_id'][:8]}...)")
        rating_str = input("Enter rating (1-5): ").strip()
        if not rating_str.isdigit():
            print("[!] Rating must be a number")
            return
        rating = int(rating_str)
        if rating < 1 or rating > 5:
            print("[!] Rating must be between 1 and 5")
            return
        comment = input("Enter comment (optional): ").strip()

        send_json(self.sock, {
            "action": "submit_review",
            "game_id": game["game_id"],
            "rating": rating,
            "comment": comment,
        })
        resp = recv_json(self.sock)
        if resp and resp.get("status") == "ok":
            print("[OK] Review submitted successfully!")
        else:
            print(f"[!] Failed: {resp.get('message', 'Unknown error')}")

    def list_games_and_review(self) -> None:
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print(f"[!] Failed to fetch games: {resp.get('message', 'Unknown error')}")
            return
        games = resp.get("games", [])
        if not games:
            print("(No games available)")
            return

        print("\n=== Select Game to Review ===")
        for idx, g in enumerate(games, start=1):
            print(f"{idx}. {g['name']} (id={g['game_id'][:8]}...) by {g['developer']}")

        choice = input("Enter number (or 0 to cancel): ").strip()
        if not choice.isdigit():
            return
        idx = int(choice)
        if idx == 0:
            return
        if 1 <= idx <= len(games):
            self.submit_review(games[idx - 1])
