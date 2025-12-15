# path: games/gomoku/gomoku_client.py
import socket
import struct
import json
import argparse
import threading
from typing import Dict, Any, Optional, List

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


def print_board(board: List[List[int]], my_symbol: str, opp_symbol: str) -> None:
    size = len(board)
    print("\n   " + " ".join(f"{c:2d}" for c in range(size)))
    for r in range(size):
        row_str = f"{r:2d} "
        for c in range(size):
            cell = board[r][c]
            if cell == 0:
                ch = "."
            elif cell == 1:
                ch = my_symbol if my_symbol == "X" else opp_symbol
            elif cell == 2:
                ch = my_symbol if my_symbol == "O" else opp_symbol
            row_str += f"{ch:2s}"
        print(row_str)
    print("")


class GomokuClient:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.player_index: Optional[int] = None
        self.symbol: str = "X"
        self.board_size: int = 15
        self.board: Optional[List[List[int]]] = None

        self.your_turn = False
        self.game_over = False

    def start(self):
        self.sock.connect((self.host, self.port))
        print(f"[GomokuClient] Connected to {self.host}:{self.port}")

        # join
        send_json(self.sock, {
            "type": "join",
            "player_name": self.name,
        })

        # listener thread
        t = threading.Thread(target=self.listener_loop, daemon=True)
        t.start()

        # main input loop
        try:
            while not self.game_over:
                if not self.your_turn:
                    # avoid busy waiting
                    cmd = input("(Press Enter to refresh, or type 'quit' to leave): ").strip()
                    if cmd == "quit":
                        send_json(self.sock, {"type": "quit"})
                        break
                    continue

                print("Your turn! Enter: row col (e.g. '7 8'), or 'quit' to leave.")
                line = input("> ").strip()
                if line == "quit":
                    send_json(self.sock, {"type": "quit"})
                    break
                parts = line.split()
                if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                    print("Invalid format, please try again.")
                    continue
                row = int(parts[0])
                col = int(parts[1])
                send_json(self.sock, {
                    "type": "move",
                    "row": row,
                    "col": col,
                })
        except KeyboardInterrupt:
            print("\n[GomokuClient] Interrupted.")
        except Exception as e:
            print(f"[GomokuClient] Error: {e}")
        finally:
            try:
                self.sock.close()
            except:
                pass
            print("[GomokuClient] Disconnected.")

    def listener_loop(self):
        try:
            while True:
                msg = recv_json(self.sock)
                if msg is None:
                    print("[GomokuClient] Server disconnected.")
                    self.game_over = True
                    break
                self.handle_message(msg)
        except ConnectionError:
            print("[GomokuClient] Connection error.")
            self.game_over = True

    def handle_message(self, msg: Dict[str, Any]):
        mtype = msg.get("type")
        if mtype == "welcome":
            self.player_index = msg.get("player_index")
            self.symbol = msg.get("symbol", "X")
            self.board_size = msg.get("board_size", 15)
            print(f"Welcome {self.name}! You are Player {self.player_index}, symbol '{self.symbol}'.")
        elif mtype == "start":
            self.board = msg.get("board")
            self.your_turn = bool(msg.get("your_turn", False))
            print("Game started!")
            print_board(self.board, self.symbol, "O" if self.symbol == "X" else "X")
            if self.your_turn:
                print("You go first.")
            else:
                print("Waiting for opponent...")
        elif mtype == "board_update":
            self.board = msg.get("board")
            self.your_turn = bool(msg.get("your_turn", False))
            print_board(self.board, self.symbol, "O" if self.symbol == "X" else "X")
            if self.your_turn:
                print("Your turn.")
            else:
                print("Waiting for opponent...")
        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            if result == "win":
                print("You win!")
            elif result == "lose":
                print("You lose.")
            else:
                print("Draw.")
        elif mtype == "opponent_quit":
            print("Opponent left the game. Game over.")
            self.game_over = True
        elif mtype == "error":
            print("Error:", msg.get("message"))
        else:
            print("Unknown message:", msg)


def main():
    parser = argparse.ArgumentParser(description="Gomoku Game Client")
    parser.add_argument("--host", required=True, help="Game server host")
    parser.add_argument("--port", type=int, required=True, help="Game server port")
    parser.add_argument("--name", required=True, help="Your player name")
    args = parser.parse_args()

    client = GomokuClient(args.host, args.port, args.name)
    client.start()


if __name__ == "__main__":
    main()
