# path: server/utils.py
import os
import threading
from datetime import datetime


LOG_LOCK = threading.Lock()


def log(*args) -> None:
    """Very simple synchronized logger."""
    with LOG_LOCK:
        prefix = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(prefix, *args, flush=True)


# Default configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 10001

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "server", "db")
STORAGE_DIR = os.path.join(BASE_DIR, "server", "storage")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)
