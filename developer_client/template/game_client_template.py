# path: template/game_client_template.py
"""
Game Client Template
====================
This is a template for creating a multiplayer game client.
Customize the display and input handling for your game.

Usage: python {game_name}_client.py --host <host> --port <port> --name <player_name>
"""

import socket
import struct
import json
import argparse
import threading
from typing import Dict, Any, Optional

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


class GameClient:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.player_index: Optional[int] = None
        self.game_state: Dict[str, Any] = {}
        self.your_turn = False
        self.game_over = False

    def start(self):
        self.sock.connect((self.host, self.port))
        print(f"[GameClient] Connected to {self.host}:{self.port}")

        # Send join request
        send_json(self.sock, {
            "type": "join",
            "player_name": self.name,
        })

        # Start listener thread
        t = threading.Thread(target=self.listener_loop, daemon=True)
        t.start()

        # Main input loop
        try:
            while not self.game_over:
                if not self.your_turn:
                    cmd = input("(Press Enter to refresh, or type 'quit' to leave): ").strip()
                    if cmd == "quit":
                        send_json(self.sock, {"type": "quit"})
                        break
                    continue

                self.display_game()
                print("Your turn! Enter your move (or 'quit' to leave):")
                line = input("> ").strip()
                
                if line == "quit":
                    send_json(self.sock, {"type": "quit"})
                    break
                
                move = self.parse_input(line)
                if move:
                    send_json(self.sock, {"type": "move", **move})
                else:
                    print("Invalid input, please try again.")
                    
        except KeyboardInterrupt:
            print("\n[GameClient] Interrupted.")
        except Exception as e:
            print(f"[GameClient] Error: {e}")
        finally:
            try:
                self.sock.close()
            except:
                pass
            print("[GameClient] Disconnected.")

    def listener_loop(self):
        try:
            while True:
                msg = recv_json(self.sock)
                if msg is None:
                    print("[GameClient] Server disconnected.")
                    self.game_over = True
                    break
                self.handle_message(msg)
        except ConnectionError:
            print("[GameClient] Connection error.")
            self.game_over = True

    def handle_message(self, msg: Dict[str, Any]):
        mtype = msg.get("type")
        
        if mtype == "welcome":
            self.player_index = msg.get("player_index")
            print(f"Welcome {self.name}! You are Player {self.player_index}.")
            print("Waiting for other players...")
            
        elif mtype == "start":
            self.game_state = msg.get("game_state", {})
            self.your_turn = bool(msg.get("your_turn", False))
            print("Game started!")
            self.display_game()
            if self.your_turn:
                print("You go first.")
            else:
                print("Waiting for opponent...")
                
        elif mtype == "state_update":
            self.game_state = msg.get("game_state", {})
            self.your_turn = bool(msg.get("your_turn", False))
            self.display_game()
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
                
        elif mtype == "player_quit":
            print("Opponent left the game. Game over.")
            self.game_over = True
            
        elif mtype == "error":
            print("Error:", msg.get("message"))
            
        else:
            print("Unknown message:", msg)

    def display_game(self):
        """
        Override this method to display your game state.
        """
        print("\n--- Game State ---")
        print(self.game_state)
        print("------------------\n")

    def parse_input(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Override this method to parse player input into a move dict.
        Return None if input is invalid.
        """
        # Example: parse "row col" format
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return {"row": int(parts[0]), "col": int(parts[1])}
        return None


def main():
    parser = argparse.ArgumentParser(description="Game Client")
    parser.add_argument("--host", required=True, help="Game server host")
    parser.add_argument("--port", type=int, required=True, help="Game server port")
    parser.add_argument("--name", required=True, help="Your player name")
    args = parser.parse_args()

    client = GameClient(args.host, args.port, args.name)
    client.start()


if __name__ == "__main__":
    main()
