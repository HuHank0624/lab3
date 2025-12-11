# path: developer_client/utils.py
import socket
import json
import struct
import base64
from typing import Dict, Any, Optional

# -----------------------------
# TCP JSON framing
# -----------------------------

HEADER_FMT = "!I"  # 4 bytes length prefix


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    payload = json.dumps(obj).encode("utf-8")
    header = struct.pack(HEADER_FMT, len(payload))
    sock.sendall(header + payload)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed")
        buf += chunk
    return buf


def recv_json(sock: socket.socket) -> Optional[Dict[str, Any]]:
    try:
        header = recv_exact(sock, struct.calcsize(HEADER_FMT))
    except ConnectionError:
        return None
    length = struct.unpack(HEADER_FMT, header)[0]
    if length == 0:
        return {}
    payload = recv_exact(sock, length)
    try:
        return json.loads(payload.decode("utf-8"))
    except:
        return {"error": "Invalid JSON", "raw": payload}


# -----------------------------
# Base64 chunk helpers
# -----------------------------

def encode_chunk(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
