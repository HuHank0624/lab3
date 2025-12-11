# path: player_client/utils.py
import socket
import json
import struct
import base64
from pathlib import Path
from typing import Dict, Any, Optional

HEADER_FMT = "!I"  # 4-byte length prefix


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    payload = json.dumps(obj).encode("utf-8")
    header = struct.pack(HEADER_FMT, len(payload))
    sock.sendall(header + payload)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed")
        buf += chunk
    return buf


def recv_json(sock: socket.socket) -> Optional[Dict[str, Any]]:
    try:
        header = _recv_exact(sock, struct.calcsize(HEADER_FMT))
    except ConnectionError:
        return None
    (length,) = struct.unpack(HEADER_FMT, header)
    if length == 0:
        return {}
    payload = _recv_exact(sock, length)
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return {"error": "invalid_json", "raw": payload.decode("utf-8", errors="replace")}


def encode_chunk(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_chunk(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


# ---------- local directories for this player client ----------

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_ROOT = BASE_DIR / "downloads"      # downloads/<username>/
GAMES_ROOT = BASE_DIR / "games"             # games/<game_id>_<name>/
DOWNLOAD_ROOT.mkdir(exist_ok=True)
GAMES_ROOT.mkdir(exist_ok=True)
