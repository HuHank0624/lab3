# path: template/game_server_template.py
"""
Game Server Template
====================
This is a template for creating a multiplayer game server.
Customize the game logic in the GameLogic class.

Usage: python {game_name}_server.py --port <port>
"""

import socket
import threading
import struct
import json
import argparse
from typing import List, Dict, Any, Optional

HEADER_FMT = "!I"


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    data = json.dumps(obj).encode("utf-8")
    header = struct.pack(HEADER_FMT, len(data))
    sock.sendall(header + data)


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
    (length,) = struct.unpack(HEADER_FMT, header)
    if length == 0:
        return {}
    payload = recv_exact(sock, length)
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return {"type": "error", "message": "Invalid JSON"}


class GameLogic:
    """
    Implement your game logic here.
    Override methods as needed for your specific game.
    """
    
    def __init__(self, max_players: int = 2):
        self.max_players = max_players
        self.current_player: int = 0
        self.winner: Optional[int] = None
        self.game_state: Dict[str, Any] = {}
    
    def initialize_game(self) -> None:
        """Called when all players have joined and game starts."""
        pass
    
    def process_move(self, player_idx: int, move: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a player's move.
        Returns: {"valid": bool, "message": str, "game_over": bool, "winner": int or None}
        """
        # Override this method with your game logic
        return {"valid": True, "message": "OK", "game_over": False, "winner": None}
    
    def get_state(self) -> Dict[str, Any]:
        """Return current game state to broadcast to players."""
        return self.game_state


class GameServer:
    def __init__(self, host: str, port: int, max_players: int = 2):
        self.host = host
        self.port = port
        self.max_players = max_players
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.game = GameLogic(max_players)
        self.clients: List[socket.socket] = []
        self.names: List[str] = [""] * max_players
        self.lock = threading.Lock()
        self.game_started = False

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print(f"[GameServer] Listening on {self.host}:{self.port}")
        print(f"Waiting for {self.max_players} players to join...")

        while len(self.clients) < self.max_players:
            client_sock, addr = self.sock.accept()
            print(f"[GameServer] New connection from {addr}")
            t = threading.Thread(target=self.handle_client_join, args=(client_sock,), daemon=True)
            t.start()

        while not self.game_started:
            pass

        print("[GameServer] Game started. Waiting for moves...")
        try:
            while self.game.winner is None:
                pass
        except KeyboardInterrupt:
            print("[GameServer] Shutting down.")
        finally:
            self.sock.close()

    def handle_client_join(self, sock: socket.socket):
        try:
            msg = recv_json(sock)
            if not msg or msg.get("type") != "join":
                send_json(sock, {"type": "error", "message": "Must send join first"})
                sock.close()
                return

            player_name = msg.get("player_name", "Anonymous")

            with self.lock:
                if len(self.clients) >= self.max_players:
                    send_json(sock, {"type": "error", "message": "Game is full"})
                    sock.close()
                    return
                player_index = len(self.clients)
                self.clients.append(sock)
                self.names[player_index] = player_name

            send_json(sock, {
                "type": "welcome",
                "player_index": player_index,
                "player_name": player_name,
                "max_players": self.max_players,
            })
            print(f"[GameServer] Player {player_index} ({player_name}) joined.")

            if len(self.clients) == self.max_players and not self.game_started:
                self.start_game()

            self.client_loop(sock, player_index)

        except ConnectionError:
            print("[GameServer] Connection error during join.")
            sock.close()

    def start_game(self):
        with self.lock:
            self.game_started = True
            self.game.initialize_game()
        
        print("[GameServer] All players ready. Starting game.")
        for idx, sock in enumerate(self.clients):
            send_json(sock, {
                "type": "start",
                "your_turn": (idx == self.game.current_player),
                "game_state": self.game.get_state(),
            })

    def client_loop(self, sock: socket.socket, player_index: int):
        try:
            while True:
                msg = recv_json(sock)
                if msg is None:
                    print(f"[GameServer] Player {player_index} disconnected.")
                    self.broadcast_player_quit(player_index)
                    break

                msg_type = msg.get("type")
                if msg_type == "move":
                    self.handle_move(player_index, msg)
                elif msg_type == "quit":
                    print(f"[GameServer] Player {player_index} quit.")
                    self.broadcast_player_quit(player_index)
                    break
                else:
                    send_json(sock, {"type": "error", "message": "Unknown message type"})
        except ConnectionError:
            print(f"[GameServer] Player {player_index} connection lost.")
            self.broadcast_player_quit(player_index)
        finally:
            sock.close()

    def handle_move(self, player_index: int, msg: Dict[str, Any]):
        with self.lock:
            if player_index != self.game.current_player:
                send_json(self.clients[player_index], {"type": "error", "message": "Not your turn"})
                return

            result = self.game.process_move(player_index, msg)
            
            if not result["valid"]:
                send_json(self.clients[player_index], {"type": "error", "message": result["message"]})
                return

            # Switch turn
            self.game.current_player = (self.game.current_player + 1) % self.max_players

            # Broadcast state update
            for idx, sock in enumerate(self.clients):
                send_json(sock, {
                    "type": "state_update",
                    "game_state": self.game.get_state(),
                    "your_turn": (idx == self.game.current_player),
                    "last_move": msg,
                })

            # Check game over
            if result["game_over"]:
                self.game.winner = result["winner"]
                for idx, sock in enumerate(self.clients):
                    if result["winner"] is None:
                        outcome = "draw"
                    elif idx == result["winner"]:
                        outcome = "win"
                    else:
                        outcome = "lose"
                    send_json(sock, {
                        "type": "game_over",
                        "result": outcome,
                    })

    def broadcast_player_quit(self, leaver_index: int):
        for idx, sock in enumerate(self.clients):
            if idx != leaver_index:
                try:
                    send_json(sock, {"type": "player_quit", "player_index": leaver_index})
                except:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Game Server")
    parser.add_argument("--host", default="0.0.0.0", help="IP to bind")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--players", type=int, default=2, help="Number of players")
    args = parser.parse_args()

    server = GameServer(args.host, args.port, args.players)
    server.start()


if __name__ == "__main__":
    main()
