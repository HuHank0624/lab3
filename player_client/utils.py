# path: player_client/utils.py
import socket
import json
import struct
import base64
from pathlib import Path
from typing import Dict, Any, Optional

HEADER_FMT = "!I"  # 4-byte length prefix
# ---------- local directories for this player client ----------

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_ROOT = BASE_DIR / "downloads"      # downloads/<username>/
GAMES_ROOT = BASE_DIR / "games"             # games/<game_id>_<name>/
DOWNLOAD_ROOT.mkdir(exist_ok=True)
GAMES_ROOT.mkdir(exist_ok=True)
