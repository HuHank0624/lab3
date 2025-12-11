# path: player_client/library.py
from pathlib import Path
from typing import List

from .utils import GAMES_ROOT


class GameLibrary:
    """
    管理本地遊戲庫：簡單以 games/ 底下資料夾代表一個已安裝遊戲。
    資料夾命名約定：<game_id>_<name>/
    """

    def __init__(self, username: str):
        self.username = username

    def list_installed_games(self) -> List[Path]:
        if not GAMES_ROOT.exists():
            return []
        return [p for p in GAMES_ROOT.iterdir() if p.is_dir()]

    def show_library(self) -> None:
        print("\n=== 我的遊戲庫 ===")
        games = self.list_installed_games()
        if not games:
            print("(尚未安裝任何遊戲)")
            return
        for idx, p in enumerate(games, start=1):
            print(f"{idx}. {p.name}  (路徑: {p})")
