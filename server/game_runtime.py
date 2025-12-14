# path: server/game_runtime.py

import os
import sys
import zipfile
import subprocess
from typing import Optional, Dict, Any

from .utils import STORAGE_DIR, log


RUNTIME_DIR = os.path.join(STORAGE_DIR, "runtime")
os.makedirs(RUNTIME_DIR, exist_ok=True)


class GameRuntime:
    """
    負責：
    1. 將上架的 zip 解壓到 runtime 目錄
    2. 回傳該遊戲的 server_entry / client_entry 的實際檔案路徑
    3. 啟動遊戲的 game_server subprocess
    """

    def __init__(self):
        self.running_servers = {}  # room_id -> subprocess.Popen(...)

    def prepare_game(self, game: Dict[str, Any]) -> Dict[str, str]:
        """
        解壓遊戲 zip，回傳解壓後的路徑與 entrypoints。
        """
        game_id = game["game_id"]
        version = game["version"]
        zip_path = game["file_path"]

        extract_dir = os.path.join(RUNTIME_DIR, f"{game_id}_{version}")
        os.makedirs(extract_dir, exist_ok=True)

        # 解壓縮（如果已經解過，就跳過）
        marker_path = os.path.join(extract_dir, ".unzipped")
        if not os.path.exists(marker_path):
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            open(marker_path, "w").close()  # 只寫一個 marker

        # Note: gui_entry stores the server entry file name
        cli_entry = os.path.join(extract_dir, game.get("cli_entry", ""))
        server_entry = os.path.join(extract_dir, game.get("gui_entry", ""))
        
        # Fallback: try to derive server entry from cli entry
        if not server_entry or not os.path.exists(server_entry):
            server_entry = os.path.join(extract_dir, game.get("cli_entry", "").replace("_client", "_server"))

        return {
            "extract_dir": extract_dir,
            "cli_entry": cli_entry,
            "server_entry": server_entry,
        }

    def start_game_server(self, room_id: str, game: Dict[str, Any], port: int) -> bool:
        """
        用 subprocess 啟動該遊戲的 server_entry。
        """
        prep = self.prepare_game(game)
        server_entry = prep["server_entry"]

        if not os.path.exists(server_entry):
            log(f"[Runtime] server_entry not found: {server_entry}")
            return False

        cmd = [sys.executable, server_entry, "--port", str(port)]
        log(f"[Runtime] Launching Game Server: {cmd}")

        proc = subprocess.Popen(cmd)
        self.running_servers[room_id] = proc
        return True
