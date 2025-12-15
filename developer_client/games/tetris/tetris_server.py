# path: games/tetris/tetris_server.py
"""
Tetris Battle Game Server
Supports 2 players competing in real-time
"""
import socket
import threading
import struct
import json
import argparse
import time
import random
from typing import List, Dict, Any, Optional

HEADER_FMT = "!I"

# Tetris board dimensions
ROWS = 20
COLS = 10

# Tetromino shapes (row, col) offsets for each rotation state
SHAPES = {
    'I': [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    'O': [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    'T': [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (1, 1), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    'S': [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, 1), (1, 2), (0, 0), (0, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    'Z': [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    'L': [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
    'J': [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
}

SHAPE_COLORS = {
    'I': 1, 'O': 2, 'T': 3, 'S': 4, 'Z': 5, 'L': 6, 'J': 7
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


class TetrisPlayer:
    """Represents one player's game state."""
    def __init__(self, player_id: int, sock: socket.socket, name: str):
        self.player_id = player_id
        self.sock = sock
        self.name = name
        self.board: List[List[int]] = [[0] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines_cleared = 0
        self.game_over = False
        
        # Current piece state
        self.current_piece: Optional[str] = None
        self.piece_row = 0
        self.piece_col = 0
        self.piece_rotation = 0
        
        # Next piece
        self.next_piece: Optional[str] = None
        
        # Piece bag (7-bag randomizer)
        self.bag: List[str] = []

    def get_next_piece(self) -> str:
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn_piece(self) -> bool:
        """Spawn a new piece at the top. Returns False if game over."""
        if self.next_piece:
            self.current_piece = self.next_piece
        else:
            self.current_piece = self.get_next_piece()
        
        self.next_piece = self.get_next_piece()
        self.piece_row = 0
        self.piece_col = COLS // 2 - 2
        self.piece_rotation = 0
        
        # Check if spawn is valid
        if not self.is_valid_position(self.piece_row, self.piece_col, self.piece_rotation):
            self.game_over = True
            return False
        return True

    def get_piece_cells(self, row: int, col: int, rotation: int) -> List[tuple]:
        """Get absolute cell positions for current piece."""
        if not self.current_piece:
            return []
        shape = SHAPES[self.current_piece][rotation % 4]
        return [(row + dr, col + dc) for dr, dc in shape]

    def is_valid_position(self, row: int, col: int, rotation: int) -> bool:
        """Check if piece position is valid."""
        for r, c in self.get_piece_cells(row, col, rotation):
            if r < 0 or r >= ROWS or c < 0 or c >= COLS:
                return False
            if r >= 0 and self.board[r][c] != 0:
                return False
        return True

    def move_left(self) -> bool:
        if self.is_valid_position(self.piece_row, self.piece_col - 1, self.piece_rotation):
            self.piece_col -= 1
            return True
        return False

    def move_right(self) -> bool:
        if self.is_valid_position(self.piece_row, self.piece_col + 1, self.piece_rotation):
            self.piece_col += 1
            return True
        return False

    def rotate(self) -> bool:
        new_rot = (self.piece_rotation + 1) % 4
        if self.is_valid_position(self.piece_row, self.piece_col, new_rot):
            self.piece_rotation = new_rot
            return True
        # Wall kick attempts
        for offset in [-1, 1, -2, 2]:
            if self.is_valid_position(self.piece_row, self.piece_col + offset, new_rot):
                self.piece_col += offset
                self.piece_rotation = new_rot
                return True
        return False

    def move_down(self) -> bool:
        """Move piece down. Returns False if can't move (should lock)."""
        if self.is_valid_position(self.piece_row + 1, self.piece_col, self.piece_rotation):
            self.piece_row += 1
            return True
        return False

    def hard_drop(self) -> int:
        """Drop piece to bottom. Returns number of rows dropped."""
        rows_dropped = 0
        while self.move_down():
            rows_dropped += 1
        return rows_dropped

    def lock_piece(self):
        """Lock current piece to board."""
        color = SHAPE_COLORS.get(self.current_piece, 1)
        for r, c in self.get_piece_cells(self.piece_row, self.piece_col, self.piece_rotation):
            if 0 <= r < ROWS and 0 <= c < COLS:
                self.board[r][c] = color

    def clear_lines(self) -> int:
        """Clear completed lines and return count."""
        lines_to_clear = []
        for r in range(ROWS):
            if all(self.board[r][c] != 0 for c in range(COLS)):
                lines_to_clear.append(r)
        
        for r in lines_to_clear:
            del self.board[r]
            self.board.insert(0, [0] * COLS)
        
        count = len(lines_to_clear)
        self.lines_cleared += count
        
        # Score calculation
        score_table = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
        self.score += score_table.get(count, 800)
        
        return count

    def add_garbage(self, lines: int):
        """Add garbage lines from opponent."""
        hole = random.randint(0, COLS - 1)
        for _ in range(lines):
            del self.board[0]
            garbage_line = [8] * COLS  # 8 = garbage color
            garbage_line[hole] = 0
            self.board.append(garbage_line)

    def get_board_with_piece(self) -> List[List[int]]:
        """Get board with current piece overlaid."""
        result = [row[:] for row in self.board]
        if self.current_piece:
            color = SHAPE_COLORS.get(self.current_piece, 1)
            for r, c in self.get_piece_cells(self.piece_row, self.piece_col, self.piece_rotation):
                if 0 <= r < ROWS and 0 <= c < COLS:
                    result[r][c] = color
        return result


class TetrisServer:
    def __init__(self, host: str, port: int, num_players: int = 2):
        self.host = host
        self.port = port
        self.num_players = max(2, min(num_players, 4))  # 2-4 players
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.players: Dict[int, TetrisPlayer] = {}
        self.lock = threading.Lock()
        self.game_started = False
        self.game_over = False
        self.connections_count = 0  # Track accepted connections
        
        # Game tick rate (seconds between auto-drops)
        self.tick_rate = 0.5

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[TetrisServer] Listening on {self.host}:{self.port}")
        print(f"Waiting for {self.num_players} players...")
        
        # Accept connections until we have enough players
        while self.connections_count < self.num_players:
            client_sock, addr = self.sock.accept()
            self.connections_count += 1
            print(f"[TetrisServer] Connection from {addr} ({self.connections_count}/{self.num_players})")
            t = threading.Thread(target=self.handle_join, args=(client_sock,), daemon=True)
            t.start()
        
        # Wait for game to start
        while not self.game_started:
            time.sleep(0.1)
        
        # Game loop thread
        game_thread = threading.Thread(target=self.game_loop, daemon=True)
        game_thread.start()
        
        try:
            while not self.game_over:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("[TetrisServer] Shutting down...")
        finally:
            self.sock.close()

    def handle_join(self, sock: socket.socket):
        try:
            msg = recv_json(sock)
            if not msg or msg.get("type") != "join":
                send_json(sock, {"type": "error", "message": "Must send join"})
                sock.close()
                return
            
            name = msg.get("player_name", "Player")
            
            should_start = False
            with self.lock:
                if len(self.players) >= self.num_players:
                    send_json(sock, {"type": "error", "message": "Game full"})
                    sock.close()
                    return
                
                player_id = len(self.players)
                player = TetrisPlayer(player_id, sock, name)
                self.players[player_id] = player
                
                # Check if we should start (inside lock)
                if len(self.players) == self.num_players and not self.game_started:
                    should_start = True
            
            send_json(sock, {
                "type": "welcome",
                "player_id": player_id,
                "name": name,
                "rows": ROWS,
                "cols": COLS,
                "total_players": self.num_players,
            })
            print(f"[TetrisServer] Player {player_id} ({name}) joined ({len(self.players)}/{self.num_players})")
            
            if should_start:
                self.start_game()
            
            # Handle player input
            self.player_loop(player)
            
        except Exception as e:
            print(f"[TetrisServer] Error: {e}")
            sock.close()

    def start_game(self):
        with self.lock:
            for player in self.players.values():
                player.spawn_piece()
            self.game_started = True
        
        print("[TetrisServer] Game starting!")
        for player in self.players.values():
            send_json(player.sock, {
                "type": "start",
                "board": player.get_board_with_piece(),
                "next_piece": player.next_piece,
                "score": player.score,
            })

    def player_loop(self, player: TetrisPlayer):
        try:
            while not self.game_over and not player.game_over:
                msg = recv_json(player.sock)
                if msg is None:
                    print(f"[TetrisServer] Player {player.player_id} disconnected")
                    player.game_over = True
                    self.check_winner()
                    break
                
                self.handle_input(player, msg)
        except ConnectionError:
            player.game_over = True
            self.check_winner()

    def handle_input(self, player: TetrisPlayer, msg: Dict[str, Any]):
        action = msg.get("type")
        moved = False
        
        with self.lock:
            if action == "left":
                moved = player.move_left()
            elif action == "right":
                moved = player.move_right()
            elif action == "rotate":
                moved = player.rotate()
            elif action == "down":
                moved = player.move_down()
            elif action == "drop":
                player.hard_drop()
                self.lock_and_spawn(player)
                moved = True
            elif action == "quit":
                player.game_over = True
                self.check_winner()
                return
        
        if moved:
            self.send_update(player)

    def lock_and_spawn(self, player: TetrisPlayer):
        """Lock piece and spawn new one."""
        player.lock_piece()
        lines = player.clear_lines()
        
        # Send garbage to opponent
        if lines >= 2:
            garbage_lines = lines - 1
            opponent_id = 1 - player.player_id
            if opponent_id in self.players:
                opponent = self.players[opponent_id]
                opponent.add_garbage(garbage_lines)
                self.send_update(opponent)
        
        if not player.spawn_piece():
            player.game_over = True
            self.check_winner()

    def send_update(self, player: TetrisPlayer):
        """Send board update to player."""
        try:
            send_json(player.sock, {
                "type": "update",
                "board": player.get_board_with_piece(),
                "next_piece": player.next_piece,
                "score": player.score,
                "lines": player.lines_cleared,
            })
        except:
            pass
        
        # Also send opponent state
        opponent_id = 1 - player.player_id
        if opponent_id in self.players:
            opp = self.players[opponent_id]
            try:
                send_json(player.sock, {
                    "type": "opponent_update",
                    "board": opp.get_board_with_piece(),
                    "score": opp.score,
                })
            except:
                pass

    def game_loop(self):
        """Main game tick loop."""
        while not self.game_over:
            time.sleep(self.tick_rate)
            
            with self.lock:
                for player in self.players.values():
                    if player.game_over:
                        continue
                    
                    if not player.move_down():
                        self.lock_and_spawn(player)
                    
                    self.send_update(player)

    def check_winner(self):
        """Check if game is over and announce winner."""
        with self.lock:
            alive_players = [p for p in self.players.values() if not p.game_over]
            
            if len(alive_players) <= 1:
                self.game_over = True
                
                winner = alive_players[0] if alive_players else None
                
                for player in self.players.values():
                    if winner and player.player_id == winner.player_id:
                        result = "win"
                    else:
                        result = "lose"
                    
                    try:
                        send_json(player.sock, {
                            "type": "game_over",
                            "result": result,
                            "winner_name": winner.name if winner else "No one",
                        })
                    except:
                        pass


def main():
    parser = argparse.ArgumentParser(description="Tetris Battle Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, required=True, help="Port")
    parser.add_argument("--players", type=int, default=2, help="Number of players")
    args = parser.parse_args()
    
    server = TetrisServer(args.host, args.port, args.players)
    server.start()


if __name__ == "__main__":
    main()
