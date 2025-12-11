# path: developer_client/client.py
import socket
from .menu import DeveloperMenu

SERVER_HOST = "127.0.0.1"   # or linux2.nycu.edu.tw (with ssh port forward)
SERVER_PORT = 5555


def main():
    print("Developer Client starting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")

    menu = DeveloperMenu(sock)
    menu.run()

    sock.close()


if __name__ == "__main__":
    main()
