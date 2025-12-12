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

    def _choose_game_from_owned(self) -> Optional[Dict[str, Any]]:
        """顯示 server 遊戲列表，但只列出已安裝的 game_id。"""
        games = self._fetch_games()
        installed_dirs = self.library.list_installed_games()
        installed_ids = set()
        for d in installed_dirs:
            # 資料夾名: <game_id>_<name>
            parts = d.name.split("_", 1)
            if parts:
                installed_ids.add(parts[0])

        owned_games = [g for g in games if g["game_id"] in installed_ids]
        if not owned_games:
            print("⚠ 你目前沒有安裝任何遊戲，請先到商城下載。")
            return None

        print("\n=== 以已安裝遊戲建立房間 ===")
        for idx, g in enumerate(owned_games, start=1):
            print(f"{idx}. {g['name']} (id={g['game_id']}) v{g['version']}")

        choice = input("選擇遊戲（或 0 返回）：").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(owned_games):
            return owned_games[idx - 1]
        return None

    # ----- main lobby flow -----

    def lobby_menu(self) -> None:
        while True:
            print("\n=== 遊戲大廳 ===")
            print("1. 查看房間列表")
            print("2. 建立新房間")
            print("3. 加入房間")
            print("4. 離開房間（需輸入房間ID）")
            print("5. 房主開始遊戲（需輸入房間ID）")
            print("0. 返回玩家主選單")
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
        print("\n=== 房間列表 ===")
        if not rooms:
            print("(目前沒有房間)")
            return
        for r in rooms:
            print(
                f"- room_id={r['room_id']} | {r['room_name']} | game={r['game_id']}"
                f" | host={r['host']} | players={len(r['players'])}/{r['max_players']} | "
                f"status={r['status']} | game_port={r['game_port']}"
            )

    def create_room(self) -> None:
        game = self._choose_game_from_owned()
        if not game:
            return
        room_name = input("房間名稱：").strip() or "Room"
        max_players_str = input("最大人數（預設 2）：").strip()
        max_players = int(max_players_str) if max_players_str.isdigit() else 2

        send_json(self.sock, {
            "action": "create_room",
            "game_id": game["game_id"],
            "room_name": room_name,
            "max_players": max_players,
        })
        resp = recv_json(self.sock)
        print("伺服器:", resp)

    def join_room(self) -> None:
        room_id = input("輸入要加入的 room_id：").strip()
        send_json(self.sock, {
            "action": "join_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        print("伺服器:", resp)

    def leave_room(self) -> None:
        room_id = input("輸入要離開的 room_id：").strip()
        send_json(self.sock, {
            "action": "leave_room",
            "room_id": room_id,
        })
        resp = recv_json(self.sock)
        print("伺服器:", resp)

    def start_game(self):
        room_id = input("房主請輸入要開始的 room_id：").strip()
        send_json(self.sock, {"action": "start_game", "room_id": room_id})
        resp = recv_json(self.sock)
        print("伺服器:", resp)

        if resp.get("status") != "ok":
            return

        room_info = resp["room_info"]
        game_port = resp["game_port"]
        game_id = room_info["game_id"]

        # 找到本地 game 資料夾
        game_dir = None
        for d in GAMES_ROOT.iterdir():
            if d.name.startswith(game_id):
                game_dir = d
                break
        if not game_dir:
            print("⚠ 遊戲尚未下載")
            return

        # 找 entry
        entry = None
        for f in game_dir.rglob("*client*.py"):
            entry = f
            break
        if not entry:
            print("⚠ 找不到 client entry")
            return

        # 啟動遊戲
        cmd = [sys.executable, str(entry), "--host", "127.0.0.1", "--port", str(game_port), "--name", self.username]
        print("🎮 啟動遊戲：", cmd)
        subprocess.Popen(cmd)

