# path: player_client/download.py
import os
import shutil
import zipfile
from pathlib import Path
import socket
from typing import Dict, Any, Optional
from utils.protocol import send_json, recv_json
from .utils import DOWNLOAD_ROOT, GAMES_ROOT


class GameDownloader:
    """
    「下載」流程：
      1. 呼叫 server 的 download_game（會更新 owned_games，回傳 file_path）
      2. 在同一台機器上，將 file_path 對應的 zip 複製到 downloads/<username>/
      3. 解壓到 games/<game_id>_<name>/
    """

    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    def download_game(self, game: Dict[str, Any]) -> None:
        game_id = game["game_id"]
        name = game["name"]
        print(f"\n=== 下載遊戲：{name} (id={game_id}) ===")

        # Step 1: 通知 server 我想下載
        send_json(self.sock, {
            "action": "download_game",
            "game_id": game_id,
        })
        resp = recv_json(self.sock)
        if not resp or resp.get("status") != "ok":
            print("❌ 下載請求失敗:", resp)
            return

        file_path = resp.get("file_path")
        if not file_path:
            print("❌ server 沒有提供 file_path")
            return

        src = Path(file_path)
        if not src.exists():
            print("⚠ server 的檔案路徑在本機不存在：", src)
            print("   （如果 server 跑在 linux2，player 沒掛同一個 FS，就不能這樣 copy）")
            return

        player_dl_dir = DOWNLOAD_ROOT / self.username
        player_dl_dir.mkdir(parents=True, exist_ok=True)

        dst_zip = player_dl_dir / src.name
        shutil.copyfile(src, dst_zip)
        print(f"✅ 已將遊戲 zip 複製到 {dst_zip}")

        # Step 3: 解壓到 games 目錄
        game_dir_name = f"{game_id}_{name.replace(' ', '_')}"
        game_dir = GAMES_ROOT / game_dir_name
        if game_dir.exists():
            print("⚠ 遊戲資料夾已存在，將覆蓋裡面的內容。")
        else:
            game_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(dst_zip, "r") as zf:
                zf.extractall(game_dir)
            print(f"✅ 已解壓到 {game_dir}")
        except zipfile.BadZipFile:
            print("❌ zip 檔案損毀或不是合法的 zip。")
