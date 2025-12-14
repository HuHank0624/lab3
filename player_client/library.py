# path: player_client/library.py
from pathlib import Path
from typing import List

from .utils import GAMES_ROOT


class GameLibrary:
    """
    Manage local game library: each user has their own games folder.
    Path: games/<username>/<game_name>/
    """

    def __init__(self, username: str):
        self.username = username
        self.user_games_dir = GAMES_ROOT / username

    def list_installed_games(self) -> List[Path]:
        if not self.user_games_dir.exists():
            return []
        return [p for p in self.user_games_dir.iterdir() if p.is_dir()]

    def show_library(self) -> None:
        print("\n=== My Game Library ===")
        games = self.list_installed_games()
        if not games:
            print("(No games installed)")
            return
        for idx, p in enumerate(games, start=1):
            print(f"{idx}. {p.name}  (path: {p})")
