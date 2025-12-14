# path: player_client/client.py
import socket
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .menu import PlayerMenu

try:
    from config import SERVER_HOST, SERVER_PORT
except ImportError:
    # Fallback defaults
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 10001


def main():
    print("Player Client starting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
        print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")
    except ConnectionRefusedError:
        print(f"Failed to connect to {SERVER_HOST}:{SERVER_PORT}")
        print("Make sure the server is running.")
        return

    menu = PlayerMenu(sock)
    menu.run()

    sock.close()


if __name__ == "__main__":
    main()
