# path: player_client/review.py
import socket
from typing import Dict, Any, List
from utils.protocol import send_json, recv_json


class ReviewClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    def submit_review(self, game: Dict[str, Any]) -> None:
        print("\n=== 評分與留言 ===")
        print(f"遊戲：{game['name']} (id={game['game_id']})")
        rating_str = input("請輸入評分 (1~5)：").strip()
        if not rating_str.isdigit():
            print("❌ 評分必須是數字")
            return
        rating = int(rating_str)
        comment = input("請輸入評論（可留空）：").strip()

        send_json(self.sock, {
            "action": "submit_review",
            "game_id": game["game_id"],
            "rating": rating,
            "comment": comment,
        })
        resp = recv_json(self.sock)
        print("伺服器:", resp)

    def list_games_and_review(self) -> None:
        # 先抓遊戲列表讓玩家選擇要評分哪一款
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ 無法取得遊戲列表:", resp)
            return
        games = resp.get("games", [])
        if not games:
            print("(目前沒有遊戲)")
            return

        print("\n=== 選擇要評分的遊戲 ===")
        for idx, g in enumerate(games, start=1):
            print(f"{idx}. {g['name']} (id={g['game_id']}) by {g['developer']}")

        choice = input("輸入編號（或 0 返回）：").strip()
        if not choice.isdigit():
            return
        idx = int(choice)
        if idx == 0:
            return
        if 1 <= idx <= len(games):
            self.submit_review(games[idx - 1])
