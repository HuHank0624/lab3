# path: games/tetris/tetris_client_gui.py
"""
Tetris Battle Game Client with Tkinter GUI
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
ROWS = 20
COLS = 10
CELL_SIZE = 28

# Colors for different tetrominos
COLORS = {
    0: "#1a1a2e",   # Empty (dark background)
    1: "#00d4ff",   # I - Cyan
    2: "#ffd700",   # O - Yellow
    3: "#a855f7",   # T - Purple
    4: "#22c55e",   # S - Green
    5: "#ef4444",   # Z - Red
    6: "#f97316",   # L - Orange
    7: "#3b82f6",   # J - Blue
    8: "#6b7280",   # Garbage - Gray
}


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


class TetrisGUI:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock: Optional[socket.socket] = None
        
        self.player_id = 0
        self.rows = ROWS
        self.cols = COLS
        self.board: List[List[int]] = [[0] * COLS for _ in range(ROWS)]
        self.opponent_board: List[List[int]] = [[0] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.opponent_score = 0
        self.next_piece: Optional[str] = None
        
        self.game_started = False
        self.game_over = False
        
        # GUI Setup
        self.root = tk.Tk()
        self.root.title(f"Tetris Battle - {name}")
        self.root.configure(bg="#0f0f23")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._create_widgets()
        self._bind_keys()

    def _create_widgets(self):
        # Main container
        main_frame = tk.Frame(self.root, bg="#0f0f23")
        main_frame.pack(padx=10, pady=10)
        
        # Left side - Your board
        left_frame = tk.Frame(main_frame, bg="#0f0f23")
        left_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(left_frame, text="YOU", font=("Arial", 14, "bold"), 
                 fg="#00ff88", bg="#0f0f23").pack()
        
        self.canvas = tk.Canvas(
            left_frame,
            width=COLS * CELL_SIZE,
            height=ROWS * CELL_SIZE,
            bg="#1a1a2e",
            highlightthickness=2,
            highlightbackground="#00ff88"
        )
        self.canvas.pack(pady=5)
        
        # Score display
        self.score_label = tk.Label(
            left_frame, text="Score: 0", font=("Arial", 12),
            fg="white", bg="#0f0f23"
        )
        self.score_label.pack()
        
        self.lines_label = tk.Label(
            left_frame, text="Lines: 0", font=("Arial", 12),
            fg="white", bg="#0f0f23"
        )
        self.lines_label.pack()
        
        # Center - Status and Next piece
        center_frame = tk.Frame(main_frame, bg="#0f0f23")
        center_frame.pack(side=tk.LEFT, padx=20)
        
        self.status_label = tk.Label(
            center_frame, text="Connecting...", font=("Arial", 12),
            fg="#ffd700", bg="#0f0f23"
        )
        self.status_label.pack(pady=10)
        
        tk.Label(center_frame, text="NEXT", font=("Arial", 11, "bold"),
                 fg="white", bg="#0f0f23").pack(pady=(20, 5))
        
        self.next_canvas = tk.Canvas(
            center_frame,
            width=4 * CELL_SIZE,
            height=4 * CELL_SIZE,
            bg="#1a1a2e",
            highlightthickness=1,
            highlightbackground="#444"
        )
        self.next_canvas.pack()
        
        # Controls info
        controls_frame = tk.Frame(center_frame, bg="#0f0f23")
        controls_frame.pack(pady=20)
        
        controls = [
            ("Left/Right", "Move"),
            ("Up", "Rotate"),
            ("Down", "Soft Drop"),
            ("Space", "Hard Drop"),
        ]
        for key, action in controls:
            tk.Label(controls_frame, text=f"{key}: {action}", font=("Arial", 9),
                     fg="#888", bg="#0f0f23").pack(anchor="w")
        
        # Quit button
        self.quit_btn = tk.Button(
            center_frame, text="Quit Game", command=self.quit_game,
            font=("Arial", 10, "bold"), bg="#dc2626", fg="white",
            width=10, cursor="hand2"
        )
        self.quit_btn.pack(pady=15)
        
        # Right side - Opponent board
        right_frame = tk.Frame(main_frame, bg="#0f0f23")
        right_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(right_frame, text="OPPONENT", font=("Arial", 14, "bold"),
                 fg="#ff4444", bg="#0f0f23").pack()
        
        self.opp_canvas = tk.Canvas(
            right_frame,
            width=COLS * CELL_SIZE // 2,
            height=ROWS * CELL_SIZE // 2,
            bg="#1a1a2e",
            highlightthickness=2,
            highlightbackground="#ff4444"
        )
        self.opp_canvas.pack(pady=5)
        
        self.opp_score_label = tk.Label(
            right_frame, text="Score: 0", font=("Arial", 11),
            fg="white", bg="#0f0f23"
        )
        self.opp_score_label.pack()

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.send_action("left"))
        self.root.bind("<Right>", lambda e: self.send_action("right"))
        self.root.bind("<Up>", lambda e: self.send_action("rotate"))
        self.root.bind("<Down>", lambda e: self.send_action("down"))
        self.root.bind("<space>", lambda e: self.send_action("drop"))
        self.root.bind("<Escape>", lambda e: self.quit_game())

    def send_action(self, action: str):
        if self.game_over or not self.game_started:
            return
        if self.sock:
            try:
                send_json(self.sock, {"type": action})
            except:
                pass

    def quit_game(self):
        """Quit the game."""
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

    def draw_board(self):
        """Draw the player's board."""
        self.canvas.delete("all")
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * CELL_SIZE
                y1 = r * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                
                color = COLORS.get(self.board[r][c], COLORS[0])
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#2a2a4e",
                    width=1
                )
                
                # Add 3D effect for pieces
                if self.board[r][c] != 0:
                    # Highlight
                    self.canvas.create_line(
                        x1 + 2, y1 + 2, x2 - 2, y1 + 2,
                        fill="#ffffff", width=1
                    )
                    self.canvas.create_line(
                        x1 + 2, y1 + 2, x1 + 2, y2 - 2,
                        fill="#ffffff", width=1
                    )

    def draw_opponent_board(self):
        """Draw the opponent's board (smaller)."""
        self.opp_canvas.delete("all")
        cell = CELL_SIZE // 2
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * cell
                y1 = r * cell
                x2 = x1 + cell
                y2 = y1 + cell
                
                color = COLORS.get(self.opponent_board[r][c], COLORS[0])
                self.opp_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#2a2a4e",
                    width=1
                )

    def draw_next_piece(self):
        """Draw the next piece preview."""
        self.next_canvas.delete("all")
        if not self.next_piece:
            return
        
        # Shape definitions for preview
        shapes = {
            'I': [(1, 0), (1, 1), (1, 2), (1, 3)],
            'O': [(1, 1), (1, 2), (2, 1), (2, 2)],
            'T': [(1, 1), (2, 0), (2, 1), (2, 2)],
            'S': [(1, 1), (1, 2), (2, 0), (2, 1)],
            'Z': [(1, 0), (1, 1), (2, 1), (2, 2)],
            'L': [(1, 2), (2, 0), (2, 1), (2, 2)],
            'J': [(1, 0), (2, 0), (2, 1), (2, 2)],
        }
        
        color_map = {
            'I': 1, 'O': 2, 'T': 3, 'S': 4, 'Z': 5, 'L': 6, 'J': 7
        }
        
        cells = shapes.get(self.next_piece, [])
        color = COLORS.get(color_map.get(self.next_piece, 0), COLORS[1])
        
        for r, c in cells:
            x1 = c * CELL_SIZE
            y1 = r * CELL_SIZE
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            self.next_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline="#2a2a4e"
            )

    def connect_and_run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)  # 10 second timeout for connection
            self.status_label.config(text="Connecting...")
            self.root.update()
            
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)  # Remove timeout after connection
            self.status_label.config(text="Connected! Waiting for players...")
            
            send_json(self.sock, {
                "type": "join",
                "player_name": self.name,
            })
            
            listener = threading.Thread(target=self.listener_loop, daemon=True)
            listener.start()
            
            self.root.mainloop()
            
        except socket.timeout:
            messagebox.showerror("Error", f"Connection timed out to {self.host}:{self.port}")
            self.root.destroy()
        except ConnectionRefusedError:
            messagebox.showerror("Error", f"Cannot connect to {self.host}:{self.port}\nMake sure the game server is running.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.root.destroy()

    def listener_loop(self):
        try:
            while not self.game_over:
                msg = recv_json(self.sock)
                if msg is None:
                    self.root.after(0, lambda: self.status_label.config(text="Disconnected"))
                    self.game_over = True
                    break
                self.root.after(0, lambda m=msg: self.handle_message(m))
        except ConnectionError:
            self.root.after(0, lambda: self.status_label.config(text="Connection lost"))
            self.game_over = True

    def handle_message(self, msg: Dict[str, Any]):
        mtype = msg.get("type")
        
        if mtype == "welcome":
            self.player_id = msg.get("player_id", 0)
            self.rows = msg.get("rows", ROWS)
            self.cols = msg.get("cols", COLS)
            self.status_label.config(text=f"Player {self.player_id + 1} - Waiting...")
        
        elif mtype == "start":
            self.game_started = True
            self.board = msg.get("board", self.board)
            self.next_piece = msg.get("next_piece")
            self.score = msg.get("score", 0)
            self.status_label.config(text="PLAYING!")
            self.draw_board()
            self.draw_next_piece()
        
        elif mtype == "update":
            self.board = msg.get("board", self.board)
            self.next_piece = msg.get("next_piece")
            self.score = msg.get("score", 0)
            self.lines = msg.get("lines", 0)
            self.score_label.config(text=f"Score: {self.score}")
            self.lines_label.config(text=f"Lines: {self.lines}")
            self.draw_board()
            self.draw_next_piece()
        
        elif mtype == "opponent_update":
            self.opponent_board = msg.get("board", self.opponent_board)
            self.opponent_score = msg.get("score", 0)
            self.opp_score_label.config(text=f"Score: {self.opponent_score}")
            self.draw_opponent_board()
        
        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            winner = msg.get("winner_name", "Unknown")
            
            if result == "win":
                self.status_label.config(text="YOU WIN!", fg="#00ff88")
                messagebox.showinfo("Victory!", f"Congratulations!\nYou won the game!")
            else:
                self.status_label.config(text="GAME OVER", fg="#ff4444")
                messagebox.showinfo("Game Over", f"Winner: {winner}")
        
        elif mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))


def main():
    parser = argparse.ArgumentParser(description="Tetris Battle Client (GUI)")
    parser.add_argument("--host", required=True, help="Server host")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--name", required=True, help="Your name")
    args = parser.parse_args()
    
    client = TetrisGUI(args.host, args.port, args.name)
    client.connect_and_run()


if __name__ == "__main__":
    main()
