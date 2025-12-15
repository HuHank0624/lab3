# path: games/swing/swing_client_gui.py
"""
Swing to Win - Simple Multiplayer Game Client
Press LEFT/RIGHT arrow keys to swing and score points!
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
            self.root, text="SWING TO WIN",
            font=("Arial", 18, "bold"), fg="#eee", bg="#1a1a2e"
        ).pack(pady=10)

        # Timer
        self.timer_label = tk.Label(
            self.root, text="Time: --",
            font=("Arial", 14, "bold"), fg="#e94560", bg="#1a1a2e"
        )
        self.timer_label.pack()

        # Status
        self.status_label = tk.Label(
            self.root, text="Connecting...",
            font=("Arial", 11), fg="#aaa", bg="#1a1a2e"
        )
        self.status_label.pack(pady=5)

        # Direction display
        self.dir_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.dir_frame.pack(pady=10)

        self.left_label = tk.Label(
            self.dir_frame, text="◄", font=("Arial", 40), fg="#444", bg="#1a1a2e"
        )
        self.left_label.pack(side=tk.LEFT, padx=20)

        self.right_label = tk.Label(
            self.dir_frame, text="►", font=("Arial", 40), fg="#444", bg="#1a1a2e"
        )
        self.right_label.pack(side=tk.LEFT, padx=20)

        # Instructions
        tk.Label(
            self.root, text="Press LEFT or RIGHT to swing!",
            font=("Arial", 10), fg="#888", bg="#1a1a2e"
        ).pack()

        # Scoreboard
        tk.Label(
            self.root, text="SCORES",
            font=("Arial", 11, "bold"), fg="#eee", bg="#1a1a2e"
        ).pack(pady=(10, 5))

        self.score_text = tk.Text(
            self.root, width=25, height=6,
            font=("Consolas", 10), bg="#16213e", fg="#eee",
            state=tk.DISABLED, relief=tk.FLAT
        )
        self.score_text.pack(padx=10)

        # Quit button
        tk.Button(
            self.root, text="Quit", command=self.quit_game,
            font=("Arial", 9), bg="#e94560", fg="white", width=8
        ).pack(pady=10)

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
                # Visual feedback
                if direction == "left":
                    self.left_label.config(fg="#e94560")
                    self.right_label.config(fg="#444")
                else:
                    self.right_label.config(fg="#e94560")
                    self.left_label.config(fg="#444")
            except:
                pass

    def update_scores(self, scores: List[Dict]):
        sorted_scores = sorted(scores, key=lambda x: -x.get("score", 0))
        self.score_text.config(state=tk.NORMAL)
        self.score_text.delete("1.0", tk.END)
        
        for s in sorted_scores:
            pid = s["id"]
            name = s["name"]
            score = s["score"]
            is_me = (pid == self.player_id)
            prefix = "> " if is_me else "  "
            self.score_text.insert(tk.END, f"{prefix}{name}: {score}\n")
        
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
            self.status_label.config(text="GO! Swing fast!")

        elif mtype == "state":
            time_left = msg.get("time_remaining", 0)
            self.timer_label.config(text=f"Time: {time_left}s")
            self.update_scores(msg.get("scores", []))

        elif mtype == "player_left":
            pid = msg.get("player_id")
            self.status_label.config(text=f"Player {pid + 1} left")

        elif mtype == "game_over":
            self.game_over = True
            result = msg.get("result")
            winners = msg.get("winner_names", [])
            final_scores = msg.get("final_scores", [])

            results = "\n".join([f"{s['name']}: {s['score']}" for s in final_scores])
            
            if result == "win":
                self.status_label.config(text="YOU WIN!", fg="#ffd700")
                messagebox.showinfo("Victory!", f"You won!\n\n{results}")
            else:
                self.status_label.config(text="Game Over", fg="#e94560")
                messagebox.showinfo("Game Over", f"Winner: {', '.join(winners)}\n\n{results}")

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
