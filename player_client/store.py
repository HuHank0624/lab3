import socket
from typing import List, Dict, Any, Optional

from utils.protocol import send_json, recv_json
from utils.file_transfer import decode_chunk
from .utils import DOWNLOAD_ROOT
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
            print("❌ 無法取得遊戲列表:", resp)
            self.games = []
            return
        self.games = resp.get("games", [])

    # -----------------------------
    # UI helpers
    # -----------------------------

    def show_game_list(self) -> None:
        print("\n=== 遊戲商城 ===")
        if not self.games:
            print("(目前沒有上架遊戲)")
            return
        for idx, g in enumerate(self.games, start=1):
            print(
                f"{idx}. {g['name']} (id={g['game_id']}) "
                f"by {g['developer']} v{g['version']}"
            )

    def select_game(self) -> Optional[Dict[str, Any]]:
        if not self.games:
            return None
        choice = input("輸入遊戲編號（或 0 返回）：").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(self.games):
            return self.games[idx - 1]
        return None

    # -----------------------------
    # Main store flow
    # -----------------------------

    def view_store(self) -> None:
        self.refresh_games()

        while True:
            self.show_game_list()
            print("a. 重新整理列表")
            print("d. 下載選擇的遊戲")
            print("0. 返回玩家主選單")
            choice = input("> ").strip().lower()

            if choice == "0":
                return

            elif choice == "a":
                self.refresh_games()

            elif choice == "d":
                game = self.select_game()
                if not game:
                    continue

                send_json(self.sock, {
                    "action": "download_game",
                    "game_id": game["game_id"],
                })

                game_dir = os.path.join(DOWNLOAD_ROOT, game["game_id"])
                os.makedirs(game_dir, exist_ok=True)

                zip_path = os.path.join(game_dir, f"{game['game_id']}.zip")

                print("⬇️ 開始下載...")

                with open(zip_path, "wb") as f:
                    while True:
                        msg = recv_json(self.sock)
                        if not msg:
                            print("❌ 連線中斷")
                            return

                        if msg.get("action") != "download_chunk":
                            print("❌ 非預期封包:", msg)
                            return

                        if msg.get("eof"):
                            break

                        data = msg.get("data")
                        f.write(decode_chunk(data))

                print(f"✅ 下載完成：{zip_path}")

            else:
                print("無效選項。")
