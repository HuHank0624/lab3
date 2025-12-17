# path: games/swing/swing_server.py
"""
Swing to Win - Multiplayer Game Server
Players compete by pressing arrow keys to swing a sword left/right.
Highest swing count wins when time runs out.
Supports 2-8 players.
"""
import socket
import threading
import struct
import json
import argparse
import time
from typing import Dict, Any, Optional, List

HEADER_FMT = "!I"
GAME_DURATION = 30  # seconds
MAX_PLAYERS = 8
MIN_PLAYERS = 2


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


class Player:
    def __init__(self, player_id: int, sock: socket.socket, name: str):
        self.player_id = player_id
        self.sock = sock
        self.name = name
        self.swing_count = 0
        self.last_direction = None  # 'left' or 'right'
        self.connected = True


class SwingServer:
    def __init__(self, host: str, port: int, num_players: int = 2):
        self.host = host
        self.port = port
        self.num_players = min(max(num_players, MIN_PLAYERS), MAX_PLAYERS)
        
        self.players: Dict[int, Player] = {}
        self.lock = threading.Lock()
        self.game_started = False
        self.game_over = False
        self.start_time = 0
        self.connections_count = 0
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.num_players)
        print(f"[SwingServer] Listening on {self.host}:{self.port}")
        print(f"[SwingServer] Waiting for {self.num_players} players to join...")

        # Accept connections until we have enough players
        while self.connections_count < self.num_players:
            try:
                conn, addr = self.server_socket.accept()
                self.connections_count += 1
                print(f"[SwingServer] New connection from {addr} ({self.connections_count}/{self.num_players})")
                threading.Thread(target=self.handle_player, args=(conn,), daemon=True).start()
            except:
                break

        # Wait for all players to join properly
        while len(self.players) < self.num_players and not self.game_over:
            time.sleep(0.1)

        if len(self.players) >= MIN_PLAYERS:
            self.start_game()

    def handle_player(self, sock: socket.socket):
        try:
            # Wait for join message
            msg = recv_json(sock)
            if not msg or msg.get("type") != "join":
                send_json(sock, {"type": "error", "message": "Must send join"})
                sock.close()
                return

            player_name = msg.get("player_name", "Player")

            with self.lock:
                if len(self.players) >= self.num_players:
                    send_json(sock, {"type": "error", "message": "Game full"})
                    sock.close()
                    return

                player_id = len(self.players)
                player = Player(player_id, sock, player_name)
                self.players[player_id] = player

            # Send welcome
            send_json(sock, {
                "type": "welcome",
                "player_id": player_id,
                "player_name": player_name,
                "total_players": self.num_players,
                "game_duration": GAME_DURATION,
            })
            print(f"[SwingServer] Player {player_id} ({player_name}) joined.")

            # Handle player input
            self.player_loop(player)

        except Exception as e:
            print(f"[SwingServer] Error: {e}")
            sock.close()

    def start_game(self):
        with self.lock:
            self.game_started = True
            self.start_time = time.time()

        print("[SwingServer] Game starting!")
        
        # Send start to all players
        player_list = [{"id": p.player_id, "name": p.name} for p in self.players.values()]
        for player in self.players.values():
            try:
                send_json(player.sock, {
                    "type": "start",
                    "players": player_list,
                    "duration": GAME_DURATION,
                })
            except:
                pass

        # Start game timer thread
        threading.Thread(target=self.game_timer, daemon=True).start()

    def game_timer(self):
        """Count down and end game when time is up."""
        while not self.game_over:
            elapsed = time.time() - self.start_time
            remaining = GAME_DURATION - elapsed
            
            if remaining <= 0:
                self.end_game()
                break
            
            # Broadcast time update every second
            self.broadcast_state()
            time.sleep(1)

    def player_loop(self, player: Player):
        try:
            while not self.game_over and player.connected:
                msg = recv_json(player.sock)
                if msg is None:
                    player.connected = False
                    print(f"[SwingServer] Player {player.player_id} disconnected.")
                    self.broadcast_player_left(player.player_id)
                    break

                mtype = msg.get("type")

                if mtype == "swing":
                    direction = msg.get("direction")  # 'left' or 'right'
                    if direction in ('left', 'right') and self.game_started and not self.game_over:
                        # Only count if direction changed (actual swing)
                        if player.last_direction != direction:
                            player.swing_count += 1
                            player.last_direction = direction
                            self.broadcast_state()

                elif mtype == "quit":
                    player.connected = False
                    print(f"[SwingServer] Player {player.player_id} quit.")
                    self.broadcast_player_left(player.player_id)
                    break

        except ConnectionError:
            player.connected = False
            print(f"[SwingServer] Player {player.player_id} connection lost.")

    def broadcast_state(self):
        """Send current game state to all players."""
        elapsed = time.time() - self.start_time
        remaining = max(0, GAME_DURATION - elapsed)
        
        scores = [
            {"id": p.player_id, "name": p.name, "score": p.swing_count, "direction": p.last_direction}
            for p in self.players.values()
        ]
        
        for player in self.players.values():
            if player.connected:
                try:
                    send_json(player.sock, {
                        "type": "state",
                        "time_remaining": int(remaining),
                        "scores": scores,
                    })
                except:
                    player.connected = False

    def broadcast_player_left(self, player_id: int):
        """Notify all players that someone left."""
        for player in self.players.values():
            if player.connected and player.player_id != player_id:
                try:
                    send_json(player.sock, {
                        "type": "player_left",
                        "player_id": player_id,
                    })
                except:
                    pass

    def end_game(self):
        """End the game and announce winner."""
        with self.lock:
            if self.game_over:
                return
            self.game_over = True

        # Find winner(s)
        max_score = max(p.swing_count for p in self.players.values())
        winners = [p for p in self.players.values() if p.swing_count == max_score]

        final_scores = [
            {"id": p.player_id, "name": p.name, "score": p.swing_count}
            for p in sorted(self.players.values(), key=lambda x: -x.swing_count)
        ]

        print(f"[SwingServer] Game over! Winner(s): {[w.name for w in winners]} with {max_score} swings")

        for player in self.players.values():
            if player.connected:
                is_winner = player in winners
                try:
                    send_json(player.sock, {
                        "type": "game_over",
                        "result": "win" if is_winner else "lose",
                        "final_scores": final_scores,
                        "winner_names": [w.name for w in winners],
                    })
                except:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Swing to Win Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, required=True, help="Port")
    parser.add_argument("--players", type=int, default=2, help="Number of players (2-8)")
    args = parser.parse_args()

    server = SwingServer(args.host, args.port, args.players)
    server.start()


if __name__ == "__main__":
    main()
