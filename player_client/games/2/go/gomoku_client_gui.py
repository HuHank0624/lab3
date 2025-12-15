# path: games/gomoku/gomoku_client_gui.py
"""
Gomoku Game Client with Tkinter GUI
"""
import socket
import struct
import json
import argparse
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, Optional, List

HEADER_FMT = "!I"
BOARD_SIZE = 15
CELL_SIZE = 36
STONE_RADIUS = 15


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


class GomokuGUI:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock: Optional[socket.socket] = None

        self.player_index: Optional[int] = None
        self.symbol: str = "X"
        self.board_size: int = BOARD_SIZE
        self.board: List[List[int]] = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]

        self.your_turn = False
        self.game_over = False
        self.game_started = False

        # Create GUI
        self.root = tk.Tk()
        self.root.title(f"Gomoku - {name}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._create_widgets()

    def _create_widgets(self):
        # Info frame
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=5)

        self.status_label = tk.Label(info_frame, text="Connecting...", font=("Arial", 12))
        self.status_label.pack()

        self.turn_label = tk.Label(info_frame, text="", font=("Arial", 11, "bold"))
        self.turn_label.pack()

        # Board canvas
        canvas_size = CELL_SIZE * (BOARD_SIZE + 1)
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_size,
            height=canvas_size,
            bg="#DEB887"  # burlywood
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

        # Draw board lines
        self._draw_board()

        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        self.quit_btn = tk.Button(btn_frame, text="Quit Game", command=self.quit_game)
        self.quit_btn.pack(side=tk.LEFT, padx=5)

    def _draw_board(self):
        """Draw the Go board grid."""
        for i in range(BOARD_SIZE):
            # Horizontal lines
            x1 = CELL_SIZE
            y1 = CELL_SIZE * (i + 1)
            x2 = CELL_SIZE * BOARD_SIZE
            y2 = y1
            self.canvas.create_line(x1, y1, x2, y2, fill="black")

            # Vertical lines
            x1 = CELL_SIZE * (i + 1)
            y1 = CELL_SIZE
            x2 = x1
            y2 = CELL_SIZE * BOARD_SIZE
            self.canvas.create_line(x1, y1, x2, y2, fill="black")

            # Labels
            self.canvas.create_text(
                CELL_SIZE * (i + 1), CELL_SIZE // 2,
                text=str(i), font=("Arial", 8)
            )
            self.canvas.create_text(
                CELL_SIZE // 2, CELL_SIZE * (i + 1),
                text=str(i), font=("Arial", 8)
            )

        # Star points (for standard Go board aesthetic)
        star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        for r, c in star_points:
            x = CELL_SIZE * (c + 1)
            y = CELL_SIZE * (r + 1)
            self.canvas.create_oval(
                x - 3, y - 3, x + 3, y + 3,
                fill="black"
            )

    def _draw_stone(self, row: int, col: int, player_val: int):
        """Draw a stone at the given position."""
        x = CELL_SIZE * (col + 1)
        y = CELL_SIZE * (row + 1)
        
        if player_val == 1:
            color = "black"
        elif player_val == 2:
            color = "white"
        else:
            return

        self.canvas.create_oval(
            x - STONE_RADIUS, y - STONE_RADIUS,
            x + STONE_RADIUS, y + STONE_RADIUS,
            fill=color, outline="black", width=1
        )

    def _redraw_stones(self):
        """Redraw all stones on the board."""
        # Clear existing stones (keep grid)
        self.canvas.delete("stone")
        
        for r in range(self.board_size):
            for c in range(self.board_size):
                val = self.board[r][c]
                if val != 0:
                    x = CELL_SIZE * (c + 1)
                    y = CELL_SIZE * (r + 1)
                    color = "black" if val == 1 else "white"
                    self.canvas.create_oval(
                        x - STONE_RADIUS, y - STONE_RADIUS,
                        x + STONE_RADIUS, y + STONE_RADIUS,
                        fill=color, outline="black", width=1,
                        tags="stone"
                    )

    def on_click(self, event):
        """Handle mouse click on the board."""
        if self.game_over or not self.your_turn or not self.game_started:
            return

        # Convert click coordinates to board position
        col = round((event.x - CELL_SIZE) / CELL_SIZE)
        row = round((event.y - CELL_SIZE) / CELL_SIZE)

        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            if self.board[row][col] == 0:
                send_json(self.sock, {
                    "type": "move",
                    "row": row,
                    "col": col,
                })

    def quit_game(self):
        """Send quit message and close."""
        if self.sock:
            try:
                send_json(self.sock, {"type": "quit"})
            except:
                pass
        self.game_over = True
        self.root.destroy()

    def on_close(self):
        """Handle window close."""
        self.quit_game()

    def connect_and_run(self):
        """Connect to server and start the GUI."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.update_status("Connected. Waiting for opponent...")

            # Send join message
            send_json(self.sock, {
                "type": "join",
                "player_name": self.name,
            })

            # Start listener thread
            listener = threading.Thread(target=self.listener_loop, daemon=True)
            listener.start()

            # Run the GUI main loop
            self.root.mainloop()

        except ConnectionRefusedError:
            messagebox.showerror("Error", f"Cannot connect to {self.host}:{self.port}")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.root.destroy()

    def listener_loop(self):
        """Listen for messages from server."""
        try:
            while not self.game_over:
                msg = recv_json(self.sock)
                if msg is None:
                    self.root.after(0, lambda: self.update_status("Server disconnected"))
                    self.game_over = True
                    break
                self.root.after(0, lambda m=msg: self.handle_message(m))
        except ConnectionError:
            self.root.after(0, lambda: self.update_status("Connection error"))
            self.game_over = True

    def handle_message(self, msg: Dict[str, Any]):
        """Handle a message from server."""
        mtype = msg.get("type")
        print(f"[DEBUG] Received message type: {mtype}, content: {msg}")

        if mtype == "welcome":
            self.player_index = msg.get("player_index")
            self.symbol = msg.get("symbol", "X")
            self.board_size = msg.get("board_size", 15)
            print(f"[DEBUG] Welcome - player_index={self.player_index}, symbol={self.symbol}")
            self.update_status(f"You are Player {self.player_index + 1} ({self.symbol})")

        elif mtype == "start":
            self.board = msg.get("board", self.board)
            self.your_turn = bool(msg.get("your_turn", False))
            self.game_started = True
            print(f"[DEBUG] Start - your_turn={self.your_turn}")
            self._redraw_stones()
            self.update_turn()
            self.update_status("Game started!")

        elif mtype == "board_update":
            self.board = msg.get("board", self.board)
            self.your_turn = bool(msg.get("your_turn", False))
            self._redraw_stones()
            
            # Highlight last move
            last_move = msg.get("last_move")
            if last_move:
                r, c = last_move["row"], last_move["col"]
                x = CELL_SIZE * (c + 1)
                y = CELL_SIZE * (r + 1)
                self.canvas.create_rectangle(
                    x - STONE_RADIUS - 2, y - STONE_RADIUS - 2,
                    x + STONE_RADIUS + 2, y + STONE_RADIUS + 2,
                    outline="red", width=2, tags="highlight"
                )
            self.update_turn()

        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            if result == "win":
                self.update_status("You WIN!")
                messagebox.showinfo("Game Over", "Congratulations! You win!")
            elif result == "lose":
                self.update_status("You LOSE")
                messagebox.showinfo("Game Over", "You lost. Better luck next time!")
            else:
                self.update_status("DRAW")
                messagebox.showinfo("Game Over", "It's a draw!")

        elif mtype == "opponent_quit":
            self.game_over = True
            self.update_status("Opponent left")
            messagebox.showinfo("Game Over", "Opponent left the game. You win by default!")

        elif mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))

    def update_status(self, text: str):
        """Update the status label."""
        self.status_label.config(text=text)

    def update_turn(self):
        """Update turn indicator."""
        if self.game_over:
            self.turn_label.config(text="", fg="black")
        elif self.your_turn:
            self.turn_label.config(text=">>> YOUR TURN <<<", fg="green")
        else:
            self.turn_label.config(text="Waiting for opponent...", fg="gray")


def main():
    parser = argparse.ArgumentParser(description="Gomoku Game Client (GUI)")
    parser.add_argument("--host", required=True, help="Game server host")
    parser.add_argument("--port", type=int, required=True, help="Game server port")
    parser.add_argument("--name", required=True, help="Your player name")
    args = parser.parse_args()

    client = GomokuGUI(args.host, args.port, args.name)
    client.connect_and_run()


if __name__ == "__main__":
    main()
