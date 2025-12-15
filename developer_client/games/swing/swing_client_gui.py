# path: games/swing/swing_client_gui.py
"""
Swing to Win - Multiplayer Game Client with Tkinter GUI
Press LEFT/RIGHT arrow keys to swing the sword and score points!
"""
import socket
import struct
import json
import argparse
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, Optional, List
import math

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


# Colors for different players
PLAYER_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
]


class SwingGUI:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock: Optional[socket.socket] = None

        self.player_id = 0
        self.players: List[Dict] = []
        self.scores: Dict[int, int] = {}
        self.directions: Dict[int, str] = {}
        self.time_remaining = 0
        self.game_duration = 30

        self.game_started = False
        self.game_over = False

        # Sword animation state
        self.sword_angle = 0  # degrees, 0 = center
        self.target_angle = 0
        self.last_direction = None

        # GUI Setup
        self.root = tk.Tk()
        self.root.title(f"Swing to Win - {name}")
        self.root.configure(bg="#2C3E50")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._create_widgets()
        self._bind_keys()

    def _create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="⚔️ SWING TO WIN ⚔️",
            font=("Arial", 24, "bold"),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        title_label.pack(pady=10)

        # Timer
        self.timer_label = tk.Label(
            self.root,
            text="Time: --",
            font=("Arial", 18, "bold"),
            fg="#E74C3C",
            bg="#2C3E50"
        )
        self.timer_label.pack()

        # Status
        self.status_label = tk.Label(
            self.root,
            text="Connecting...",
            font=("Arial", 14),
            fg="#BDC3C7",
            bg="#2C3E50"
        )
        self.status_label.pack(pady=5)

        # Main game area
        game_frame = tk.Frame(self.root, bg="#2C3E50")
        game_frame.pack(padx=20, pady=10)

        # Sword canvas
        self.sword_canvas = tk.Canvas(
            game_frame,
            width=300,
            height=200,
            bg="#34495E",
            highlightthickness=2,
            highlightbackground="#ECF0F1"
        )
        self.sword_canvas.pack(pady=10)

        # Instructions
        instr_label = tk.Label(
            game_frame,
            text="Press ← LEFT or RIGHT → to swing!",
            font=("Arial", 12),
            fg="#F39C12",
            bg="#2C3E50"
        )
        instr_label.pack()

        # Scoreboard frame
        self.score_frame = tk.Frame(self.root, bg="#2C3E50")
        self.score_frame.pack(pady=10, fill=tk.X, padx=20)

        score_title = tk.Label(
            self.score_frame,
            text="📊 SCOREBOARD",
            font=("Arial", 14, "bold"),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        score_title.pack()

        # Score labels will be created dynamically
        self.score_labels: Dict[int, tk.Label] = {}

        # Quit button
        self.quit_btn = tk.Button(
            self.root,
            text="Quit Game",
            command=self.quit_game,
            font=("Arial", 12),
            bg="#E74C3C",
            fg="white"
        )
        self.quit_btn.pack(pady=10)

        # Draw initial sword
        self._draw_sword()

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.swing("left"))
        self.root.bind("<Right>", lambda e: self.swing("right"))
        self.root.focus_set()

    def _draw_sword(self):
        """Draw the sword on the canvas."""
        self.sword_canvas.delete("all")
        
        cx, cy = 150, 180  # Pivot point (bottom center)
        length = 140
        
        # Calculate sword tip position based on angle
        angle_rad = math.radians(self.sword_angle - 90)  # -90 so 0 degrees is up
        tip_x = cx + length * math.cos(angle_rad)
        tip_y = cy + length * math.sin(angle_rad)
        
        # Draw sword handle
        self.sword_canvas.create_oval(
            cx - 10, cy - 10, cx + 10, cy + 10,
            fill="#8B4513", outline="#654321", width=2
        )
        
        # Draw sword blade
        self.sword_canvas.create_line(
            cx, cy, tip_x, tip_y,
            fill="#C0C0C0", width=8, capstyle=tk.ROUND
        )
        
        # Draw sword edge (shiny effect)
        self.sword_canvas.create_line(
            cx, cy, tip_x, tip_y,
            fill="#FFFFFF", width=2, capstyle=tk.ROUND
        )
        
        # Draw crossguard
        guard_angle = math.radians(self.sword_angle)
        g1_x = cx + 20 * math.cos(guard_angle)
        g1_y = cy + 20 * math.sin(guard_angle)
        g2_x = cx - 20 * math.cos(guard_angle)
        g2_y = cy - 20 * math.sin(guard_angle)
        self.sword_canvas.create_line(
            g1_x, g1_y, g2_x, g2_y,
            fill="#FFD700", width=6, capstyle=tk.ROUND
        )

        # Draw direction indicators
        self.sword_canvas.create_text(30, 100, text="←", font=("Arial", 24), fill="#3498DB")
        self.sword_canvas.create_text(270, 100, text="→", font=("Arial", 24), fill="#3498DB")

    def _animate_sword(self):
        """Animate sword swing."""
        if abs(self.sword_angle - self.target_angle) > 1:
            diff = self.target_angle - self.sword_angle
            self.sword_angle += diff * 0.3
            self._draw_sword()
            self.root.after(16, self._animate_sword)
        else:
            self.sword_angle = self.target_angle
            self._draw_sword()

    def swing(self, direction: str):
        """Send swing command to server."""
        if not self.game_started or self.game_over:
            return

        if self.sock:
            try:
                send_json(self.sock, {"type": "swing", "direction": direction})
                # Animate sword locally
                self.target_angle = -45 if direction == "left" else 45
                self._animate_sword()
            except:
                pass

    def update_scores(self, scores: List[Dict]):
        """Update the scoreboard display."""
        # Sort by score descending
        sorted_scores = sorted(scores, key=lambda x: -x.get("score", 0))
        
        for score_data in sorted_scores:
            pid = score_data["id"]
            name = score_data["name"]
            score = score_data["score"]
            direction = score_data.get("direction", "")
            
            # Highlight current player
            is_me = (pid == self.player_id)
            color = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
            
            if pid not in self.score_labels:
                label = tk.Label(
                    self.score_frame,
                    text="",
                    font=("Arial", 12, "bold" if is_me else "normal"),
                    fg=color,
                    bg="#2C3E50"
                )
                label.pack(anchor=tk.W)
                self.score_labels[pid] = label
            
            dir_icon = "←" if direction == "left" else ("→" if direction == "right" else "•")
            me_marker = " ⭐" if is_me else ""
            self.score_labels[pid].config(
                text=f"{dir_icon} {name}: {score} swings{me_marker}"
            )

    def quit_game(self):
        if self.sock:
            try:
                send_json(self.sock, {"type": "quit"})
            except:
                pass
        self.game_over = True
        self.root.destroy()

    def on_close(self):
        self.quit_game()

    def connect_and_run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.status_label.config(text="Connected! Waiting for players...")

            send_json(self.sock, {
                "type": "join",
                "player_name": self.name,
            })

            listener = threading.Thread(target=self.listener_loop, daemon=True)
            listener.start()

            self.root.mainloop()

        except ConnectionRefusedError:
            messagebox.showerror("Error", f"Cannot connect to {self.host}:{self.port}")
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
            total = msg.get("total_players", 2)
            self.game_duration = msg.get("game_duration", 30)
            self.status_label.config(text=f"You are Player {self.player_id + 1}. Waiting for {total} players...")

        elif mtype == "start":
            self.players = msg.get("players", [])
            self.game_started = True
            self.status_label.config(text="Game started! SWING!")
            self.timer_label.config(text=f"Time: {self.game_duration}")

        elif mtype == "state":
            self.time_remaining = msg.get("time_remaining", 0)
            self.timer_label.config(text=f"Time: {self.time_remaining}")
            scores = msg.get("scores", [])
            self.update_scores(scores)

        elif mtype == "player_left":
            pid = msg.get("player_id")
            self.status_label.config(text=f"Player {pid + 1} left the game")

        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            winners = msg.get("winner_names", [])
            final_scores = msg.get("final_scores", [])

            # Build results string
            results_text = "Final Scores:\n"
            for i, s in enumerate(final_scores):
                results_text += f"{i+1}. {s['name']}: {s['score']} swings\n"

            if result == "win":
                self.status_label.config(text="🏆 YOU WIN! 🏆", fg="#F1C40F")
                messagebox.showinfo("Victory!", f"Congratulations! You won!\n\n{results_text}")
            else:
                self.status_label.config(text="Game Over", fg="#E74C3C")
                messagebox.showinfo("Game Over", f"Winner: {', '.join(winners)}\n\n{results_text}")

        elif mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))


def main():
    parser = argparse.ArgumentParser(description="Swing to Win Client (GUI)")
    parser.add_argument("--host", required=True, help="Game server host")
    parser.add_argument("--port", type=int, required=True, help="Game server port")
    parser.add_argument("--name", required=True, help="Your player name")
    args = parser.parse_args()

    client = SwingGUI(args.host, args.port, args.name)
    client.connect_and_run()


if __name__ == "__main__":
    main()
