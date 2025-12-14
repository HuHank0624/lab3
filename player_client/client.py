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
        print(f"[!] Failed to connect to {SERVER_HOST}:{SERVER_PORT}")
        print("    Make sure the server is running: make server")
        return
    except socket.gaierror:
        print(f"[!] Cannot resolve hostname: {SERVER_HOST}")
        print("    Check your network connection and server address.")
        return
    except OSError as e:
        print(f"[!] Connection error: {e}")
        return

    try:
        menu = PlayerMenu(sock)
        menu.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except BrokenPipeError:
        print("\n[!] Lost connection to server.")
    except ConnectionResetError:
        print("\n[!] Connection reset by server.")
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
    finally:
        try:
            sock.close()
        except:
            pass


if __name__ == "__main__":
    main()
