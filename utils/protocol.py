# path: utils/protocol.py
import json
import struct
from typing import Any, Dict, Optional
import socket

_HEADER_FMT = "!I"  # 4-byte big-endian length prefix


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes or raise ConnectionError."""
    chunks = []
    remaining = n
    while remaining > 0:
        try:
            chunk = sock.recv(remaining)
        except socket.timeout:
            raise ConnectionError("Socket timeout while receiving data")
        except OSError as e:
            raise ConnectionError(f"Socket error: {e}")
        if not chunk:
            raise ConnectionError("Socket closed while receiving data")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    """Serialize obj as JSON and send with 4-byte length prefix."""
    try:
        payload = json.dumps(obj).encode("utf-8")
        header = struct.pack(_HEADER_FMT, len(payload))
        sock.sendall(header + payload)
    except (BrokenPipeError, ConnectionResetError, OSError) as e:
        raise ConnectionError(f"Failed to send: {e}")


def recv_json(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """
    Receive a length-prefixed JSON object.
    Return None if connection closed cleanly before header.
    """
    try:
        header = _recv_exact(sock, struct.calcsize(_HEADER_FMT))
    except ConnectionError:
        return None
    if not header:
        return None
    (length,) = struct.unpack(_HEADER_FMT, header)
    if length == 0:
        return {}
    # Sanity check: prevent memory exhaustion from malformed packets
    if length > 100 * 1024 * 1024:  # 100MB max
        return {"action": "__packet_too_large__", "length": length}
    try:
        payload = _recv_exact(sock, length)
    except ConnectionError:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        return {"action": "__invalid_json__", "error": str(e), "raw": payload.decode("utf-8", errors="replace")[:200]}


def send_error(sock: socket.socket, message: str, **extra: Any) -> None:
    resp = {"status": "error", "message": message}
    resp.update(extra)
    send_json(sock, resp)


def send_ok(sock: socket.socket, **extra: Any) -> None:
    resp = {"status": "ok"}
    resp.update(extra)
    send_json(sock, resp)
