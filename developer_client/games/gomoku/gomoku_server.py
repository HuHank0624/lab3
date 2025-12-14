# path: games/gomoku/gomoku_server.py
import socket
import threading
import struct
import json
import argparse
from typing import List, Dict, Any, Optional, Tuple

HEADER_FMT = "!I"
BOARD_SIZE = 15
WIN_LENGTH = 5


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


class GomokuGame:
    def __init__(self, size: int = BOARD_SIZE, win_len: int = WIN_LENGTH):
        self.size = size
        self.win_len = win_len
        self.board: List[List[int]] = [[0] * size for _ in range(size)]
        self.current_player: int = 0  # 0 or 1
        self.winner: Optional[int] = None
        self.move_count: int = 0

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def place(self, player_idx: int, row: int, col: int) -> Tuple[bool, str]:
        """Try to place a stone. Return (success, message)."""
        if self.winner is not None:
            return False, "Game already finished"
        if player_idx != self.current_player:
            return False, "Not your turn"
        if not self.in_bounds(row, col):
            return False, "Out of bounds"
        if self.board[row][col] != 0:
            return False, "Cell already occupied"

        self.board[row][col] = player_idx + 1  # store 1 or 2
        self.move_count += 1

        if self.check_win(row, col):
            self.winner = player_idx
        elif self.move_count == self.size * self.size:
            self.winner = -1  # draw

        # switch turn
        self.current_player = 1 - self.current_player
        return True, "OK"

    def check_win(self, row: int, col: int) -> bool:
        """Check whether the last move at (row, col) makes a 5-in-a-row."""
        player_val = self.board[row][col]
        if player_val == 0:
            return False

        directions = [
            (1, 0),   # vertical
            (0, 1),   # horizontal
            (1, 1),   # diag down-right
            (1, -1),  # diag down-left
        ]

        for dr, dc in directions:
            count = 1
            # check forward
            r, c = row + dr, col + dc
            while 0 <= r < self.size and 0 <= c < self.size and self.board[r][c] == player_val:
                count += 1
                r += dr
                c += dc
            # check backward
            r, c = row - dr, col - dc
            while 0 <= r < self.size and 0 <= c < self.size and self.board[r][c] == player_val:
                count += 1
                r -= dr
                c -= dc
            if count >= self.win_len:
                return True
        return False

    def serialize_board(self) -> List[List[int]]:
        return [row[:] for row in self.board]


class GomokuServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.game = GomokuGame()
        self.clients: List[socket.socket] = []   # exactly 2
        self.names: List[str] = ["Player0", "Player1"]
        self.lock = threading.Lock()
        self.game_started = False

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print(f"[GomokuServer] Listening on {self.host}:{self.port}")
        print("Waiting for 2 players to join...")

        # accept in main thread for exactly 2 players
        while len(self.clients) < 2:
            client_sock, addr = self.sock.accept()
            print(f"[GomokuServer] New connection from {addr}")
            t = threading.Thread(target=self.handle_client_join, args=(client_sock,), daemon=True)
            t.start()

        # Wait until both registered
        while not self.game_started:
            pass

        print("[GomokuServer] Game started. Waiting for moves...")
        # Just wait; threads handle gameplay.
        try:
            while True:
                # game ends when both clients disconnect or winner decided & both ack
                if self.game.winner is not None:
                    # let threads finish; server can be closed by Ctrl+C
                    pass
        except KeyboardInterrupt:
            print("[GomokuServer] Shutting down.")
        finally:
            self.sock.close()

    def handle_client_join(self, sock: socket.socket):
        """Handle a new connection until it sends a valid join."""
        try:
            msg = recv_json(sock)
            if not msg or msg.get("type") != "join":
                send_json(sock, {"type": "error", "message": "Must send join first"})
                sock.close()
                return
            player_name = msg.get("player_name", "Anonymous")

            with self.lock:
                if len(self.clients) >= 2:
                    send_json(sock, {"type": "error", "message": "Game already has two players"})
                    sock.close()
                    return
                player_index = len(self.clients)
                self.clients.append(sock)
                self.names[player_index] = player_name

            symbol = "X" if player_index == 0 else "O"
            send_json(sock, {
                "type": "welcome",
                "player_index": player_index,
                "symbol": symbol,
                "board_size": self.game.size,
            })
            print(f"[GomokuServer] Player {player_index} ({player_name}) joined.")

            if len(self.clients) == 2 and not self.game_started:
                self.start_game()

            # now handle gameplay messages
            self.client_loop(sock, player_index)

        except ConnectionError:
            print("[GomokuServer] Connection error during join.")
            sock.close()

    def start_game(self):
        with self.lock:
            self.game_started = True
        print("[GomokuServer] Two players ready. Starting game.")
        for idx, sock in enumerate(self.clients):
            send_json(sock, {
                "type": "start",
                "your_turn": (idx == self.game.current_player),
                "board": self.game.serialize_board(),
            })

    def client_loop(self, sock: socket.socket, player_index: int):
        try:
            while True:
                msg = recv_json(sock)
                if msg is None:
                    print(f"[GomokuServer] Player {player_index} disconnected.")
                    self.broadcast_opponent_quit(player_index)
                    break

                msg_type = msg.get("type")
                if msg_type == "move":
                    row = int(msg.get("row", -1))
                    col = int(msg.get("col", -1))
                    self.handle_move(player_index, row, col)
                elif msg_type == "quit":
                    print(f"[GomokuServer] Player {player_index} quit.")
                    self.broadcast_opponent_quit(player_index)
                    break
                else:
                    send_json(sock, {"type": "error", "message": "Unknown message type"})
        except ConnectionError:
            print(f"[GomokuServer] Player {player_index} connection lost.")
            self.broadcast_opponent_quit(player_index)
        finally:
            sock.close()

    def handle_move(self, player_index: int, row: int, col: int):
        with self.lock:
            ok, msg = self.game.place(player_index, row, col)
            if not ok:
                send_json(self.clients[player_index], {"type": "error", "message": msg})
                return

            board = self.game.serialize_board()
            last_move = {
                "row": row,
                "col": col,
                "player_index": player_index,
            }

            # Broadcast board update
            for idx, sock in enumerate(self.clients):
                send_json(sock, {
                    "type": "board_update",
                    "board": board,
                    "last_move": last_move,
                    "your_turn": (idx == self.game.current_player),
                })

            # Check winner/draw
            if self.game.winner is not None:
                if self.game.winner == -1:
                    # draw
                    for sock in self.clients:
                        send_json(sock, {
                            "type": "game_over",
                            "result": "draw",
                            "winning_cells": [],
                        })
                else:
                    win_player = self.game.winner
                    for idx, sock in enumerate(self.clients):
                        if idx == win_player:
                            result = "win"
                        else:
                            result = "lose"
                        send_json(sock, {
                            "type": "game_over",
                            "result": result,
                            "winning_cells": [],  # 可選：計算實際五連位置
                        })

    def broadcast_opponent_quit(self, leaver_index: int):
        other = 1 - leaver_index
        if 0 <= other < len(self.clients):
            try:
                send_json(self.clients[other], {"type": "opponent_quit"})
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Gomoku Game Server")
    parser.add_argument("--host", default="0.0.0.0", help="IP to bind")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    args = parser.parse_args()

    server = GomokuServer(args.host, args.port)
    server.start()


if __name__ == "__main__":
    main()
