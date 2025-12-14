# path: server/server.py
import socket
import threading
from typing import Dict, Any

from .auth import AuthManager
from .data import DataStore
from .game_manager import GameManager
from .lobby_manager import LobbyManager
from .handlers import RequestHandlers
from .utils import *
from utils.protocol import recv_json


class GamePlatformServer:
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.datastore = DataStore()
        self.auth = AuthManager(self.datastore)
        self.games = GameManager(self.datastore)
        self.lobby = LobbyManager(self.datastore)
        self.handlers = RequestHandlers(self.datastore, self.auth, self.games, self.lobby)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self) -> None:
        self._sock.bind((self.host, self.port))
        self._sock.listen()
        log(f"Server listening on {self.host}:{self.port}")

        try:
            while True:
                client_sock, addr = self._sock.accept()
                log(f"New connection from {addr}")
                t = threading.Thread(
                    target=self._client_thread, args=(client_sock, addr), daemon=True
                )
                t.start()
        except KeyboardInterrupt:
            log("Server shutting down (KeyboardInterrupt)")
        finally:
            self._sock.close()

    def _client_thread(self, sock: socket.socket, addr) -> None:
        conn_id = id(sock)
        try:
            while True:
                msg = recv_json(sock)
                if msg is None:
                    log(f"Connection closed from {addr}")
                    break
                self.handlers.handle(sock, conn_id, msg)
        except ConnectionError:
            log(f"Connection error from {addr}")
        finally:
            self.auth.logout(conn_id)
            sock.close()


if __name__ == "__main__":
    server = GamePlatformServer()
    server.start()


def main():
    """Entry point for module execution."""
    server = GamePlatformServer()
    server.start()
