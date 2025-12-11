# path: player_client/client.py
import socket

from .menu import PlayerMenu

SERVER_HOST = "127.0.0.1"   # 若在 linux2 上跑 server + player，就填 localhost
SERVER_PORT = 5555


def main():
    print("Player Client starting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    print(f"✅ 已連線到 {SERVER_HOST}:{SERVER_PORT}")

    menu = PlayerMenu(sock)
    menu.run()

    sock.close()


if __name__ == "__main__":
    main()
