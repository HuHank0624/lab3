# path: games/swing/swing_client_gui.py
"""
Swing to Win - Multiplayer Game Client
Press LEFT/RIGHT arrow keys to swing the sword and score points!
"""
import socket
import struct
import json
import argparse
import threading
import math
import tkinter as tk
from tkinter import messagebox
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


class SwingGUI:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.sock: Optional[socket.socket] = None

        self.player_id = 0
        self.game_started = False
        self.game_over = False
        
        # Sword animation
        self.sword_angle = 0  # -45 to 45 degrees
        self.target_angle = 0

        # GUI Setup
        self.root = tk.Tk()
        self.root.title(f"Swing to Win - {name}")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._create_widgets()
        self._bind_keys()

    def _create_widgets(self):
        # Title
        tk.Label(
            self.root, text="⚔ SWING TO WIN ⚔",
            font=("Arial", 20, "bold"), fg="#ffd700", bg="#1a1a2e"
        ).pack(pady=10)

        # Timer
        self.timer_label = tk.Label(
            self.root, text="Time: --",
            font=("Arial", 16, "bold"), fg="#e94560", bg="#1a1a2e"
        )
        self.timer_label.pack()

        # Status
        self.status_label = tk.Label(
            self.root, text="Connecting...",
            font=("Arial", 11), fg="#aaa", bg="#1a1a2e"
        )
        self.status_label.pack(pady=5)

        # Sword Canvas
        self.canvas = tk.Canvas(
            self.root, width=300, height=200,
            bg="#16213e", highlightthickness=2, highlightbackground="#e94560"
        )
        self.canvas.pack(pady=10)
        self._draw_sword()

        # Instructions
        tk.Label(
            self.root, text="← Press LEFT or RIGHT to swing! →",
            font=("Arial", 12, "bold"), fg="#e94560", bg="#1a1a2e"
        ).pack(pady=5)

        # Scoreboard
        tk.Label(
            self.root, text="─── SCORES ───",
            font=("Arial", 12, "bold"), fg="#ffd700", bg="#1a1a2e"
        ).pack(pady=(10, 5))

        self.score_text = tk.Text(
            self.root, width=28, height=6,
            font=("Consolas", 11), bg="#16213e", fg="#eee",
            state=tk.DISABLED, relief=tk.FLAT
        )
        self.score_text.pack(padx=10)

        # Quit button
        tk.Button(
            self.root, text="Quit Game", command=self.quit_game,
            font=("Arial", 10, "bold"), bg="#e94560", fg="white",
            width=12, cursor="hand2"
        ).pack(pady=15)

    def _draw_sword(self):
        """Draw the sword on canvas with current angle."""
        self.canvas.delete("all")
        
        cx, cy = 150, 180  # Pivot point
        sword_length = 130
        
        angle_rad = math.radians(self.sword_angle - 90)
        tip_x = cx + sword_length * math.cos(angle_rad)
        tip_y = cy + sword_length * math.sin(angle_rad)
        
        # Blade glow
        self.canvas.create_line(cx, cy, tip_x, tip_y, width=18, fill="#4a4a8a", capstyle=tk.ROUND)
        # Main blade
        self.canvas.create_line(cx, cy, tip_x, tip_y, width=12, fill="#c0c0c0", capstyle=tk.ROUND)
        # Highlight
        hl_len = sword_length * 0.75
        hl_x = cx + hl_len * math.cos(angle_rad)
        hl_y = cy + hl_len * math.sin(angle_rad)
        self.canvas.create_line(
            cx + 15 * math.cos(angle_rad), cy + 15 * math.sin(angle_rad),
            hl_x, hl_y, width=3, fill="#ffffff", capstyle=tk.ROUND
        )
        
        # Crossguard
        perp = angle_rad + math.pi / 2
        gw = 30
        self.canvas.create_line(
            cx + gw * math.cos(perp), cy + gw * math.sin(perp),
            cx - gw * math.cos(perp), cy - gw * math.sin(perp),
            width=7, fill="#ffd700", capstyle=tk.ROUND
        )
        
        # Handle
        hl = 22
        hx = cx - hl * math.cos(angle_rad)
        hy = cy - hl * math.sin(angle_rad)
        self.canvas.create_line(cx, cy, hx, hy, width=9, fill="#8B4513", capstyle=tk.ROUND)
        
        # Pommel
        px = cx - (hl + 5) * math.cos(angle_rad)
        py = cy - (hl + 5) * math.sin(angle_rad)
        self.canvas.create_oval(px - 7, py - 7, px + 7, py + 7, fill="#ffd700", outline="#b8860b", width=2)
        
        # Direction indicators
        left_c = "#e94560" if self.sword_angle < 0 else "#444"
        right_c = "#e94560" if self.sword_angle > 0 else "#444"
        self.canvas.create_text(50, 30, text="◄", font=("Arial", 28, "bold"), fill=left_c)
        self.canvas.create_text(250, 30, text="►", font=("Arial", 28, "bold"), fill=right_c)

    def _animate_sword(self):
        """Animate sword swing."""
        if abs(self.sword_angle - self.target_angle) < 3:
            self.sword_angle = self.target_angle
            self._draw_sword()
            if self.target_angle != 0:
                self.root.after(80, self._reset_sword)
            return
        
        step = 10 if self.sword_angle < self.target_angle else -10
        self.sword_angle += step
        self._draw_sword()
        self.root.after(15, self._animate_sword)
    
    def _reset_sword(self):
        """Reset sword to center."""
        self.target_angle = 0
        self._animate_sword()

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.swing("left"))
        self.root.bind("<Right>", lambda e: self.swing("right"))
        self.root.focus_set()

    def swing(self, direction: str):
        if not self.game_started or self.game_over:
            return
        if self.sock:
            try:
                send_json(self.sock, {"type": "swing", "direction": direction})
                self.target_angle = -45 if direction == "left" else 45
                self._animate_sword()
            except:
                pass

    def update_scores(self, scores: List[Dict]):
        sorted_scores = sorted(scores, key=lambda x: -x.get("score", 0))
        self.score_text.config(state=tk.NORMAL)
        self.score_text.delete("1.0", tk.END)
        
        for i, s in enumerate(sorted_scores):
            pid = s["id"]
            name = s["name"]
            score = s["score"]
            is_me = (pid == self.player_id)
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "  "
            prefix = "► " if is_me else "  "
            self.score_text.insert(tk.END, f"{medal}{prefix}{name}: {score}\n")
        
        self.score_text.config(state=tk.DISABLED)

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
            self.sock.settimeout(15)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            self.status_label.config(text="Connected! Waiting...")

            send_json(self.sock, {"type": "join", "player_name": self.name})

            listener = threading.Thread(target=self.listener_loop, daemon=True)
            listener.start()

            self.root.mainloop()

        except ConnectionRefusedError:
            messagebox.showerror("Error", f"Cannot connect to {self.host}:{self.port}")
            self.root.destroy()
        except socket.timeout:
            messagebox.showerror("Error", "Connection timed out")
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
            self.status_label.config(text=f"Player {self.player_id + 1}/{total} - Waiting...")

        elif mtype == "start":
            self.game_started = True
            self.status_label.config(text="GO! Swing as fast as you can!", fg="#00ff00")

        elif mtype == "state":
            time_left = msg.get("time_remaining", 0)
            self.timer_label.config(text=f"Time: {time_left}s")
            if time_left <= 5:
                self.timer_label.config(fg="#ff0000")
            self.update_scores(msg.get("scores", []))

        elif mtype == "player_left":
            pid = msg.get("player_id")
            self.status_label.config(text=f"Player {pid + 1} left")

        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            winners = msg.get("winner_names", [])
            final_scores = msg.get("final_scores", [])

            results = "\n".join([f"{s['name']}: {s['score']} swings" for s in final_scores])
            
            if result == "win":
                self.status_label.config(text="🏆 YOU WIN! 🏆", fg="#ffd700")
                messagebox.showinfo("🎉 Victory!", f"Congratulations!\n\n{results}")
            else:
                self.status_label.config(text="Game Over", fg="#e94560")
                winner_str = ', '.join(winners) if winners else "No one"
                messagebox.showinfo("Game Over", f"Winner: {winner_str}\n\n{results}")

        elif mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))


def main():
    parser = argparse.ArgumentParser(description="Swing to Win Client")
    parser.add_argument("--host", required=True, help="Server host")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--name", required=True, help="Player name")
    args = parser.parse_args()

    client = SwingGUI(args.host, args.port, args.name)
    client.connect_and_run()


if __name__ == "__main__":
    main()
