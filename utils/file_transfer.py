# path: utils/file_transfer.py
import base64
from typing import Union


def encode_chunk(data: bytes) -> str:
    """Encode binary data as base64 string for JSON transport."""
    return base64.b64encode(data).decode("ascii")


def decode_chunk(data: Union[str, bytes]) -> bytes:
    """Decode base64 string/bytes back to raw bytes."""
    if isinstance(data, str):
        data = data.encode("ascii")
    return base64.b64decode(data)
