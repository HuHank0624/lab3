# path: player_client/store.py
import socket
from typing import List, Dict, Any, Optional

from .utils import send_json, recv_json
from .download import GameDownloader


class GameStoreClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username
        self.downloader = GameDownloader(sock, username)

    def fetch_games(self) -> List[Dict[str, Any]]:
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ 無法取得遊戲列表:", resp)
            return []
        return resp.get("games", [])

    def show_game_list(self, games: List[Dict[str, Any]]) -> None:
        print("\n=== 遊戲商城 ===")
        if not games:
            print("(目前沒有上架遊戲)")
            return
        for idx, g in enumerate(games, start=1):
            print(f"{idx}. {g['name']} (id={g['game_id']}) by {g['developer']} v{g['version']}")

    def select_game(self, games: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not games:
            return None
        choice = input("輸入遊戲編號（或 0 返回）：").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(games):
            return games[idx - 1]
        return None

    def view_store(self) -> None:
        games = self.fetch_games()
        while True:
            self.show_game_list(games)
            print("a. 重新整理列表")
            print("d. 下載選擇的遊戲")
            print("0. 返回玩家主選單")
            choice = input("> ").strip()

            if choice == "0":
                return
            elif choice == "a":
                games = self.fetch_games()
            elif choice == "d":
                game = self.select_game(games)
                if game:
                    self.downloader.download_game(game)
            else:
                print("無效選項。")
