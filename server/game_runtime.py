# path: server/game_runtime.py
"""
GameRuntime - Manages launching and stopping game server processes.
"""
import os
import subprocess
import sys
import zipfile
import tempfile
from typing import Dict, Any, Optional

from .utils import log, STORAGE_DIR


class GameRuntime:
    """Manages game server processes."""

    def __init__(self):
        # room_id -> subprocess.Popen
        self.running_servers: Dict[str, subprocess.Popen] = {}
        # room_id -> temp directory (for extracted game files)
        self.temp_dirs: Dict[str, str] = {}

    def start_game_server(self, room_id: str, game: Dict[str, Any], port: int) -> bool:
        """
        Start a game server for a room.
        
        Args:
            room_id: The room ID
            game: Game metadata dict with file_path, cli_entry, etc.
            port: TCP port for the game server
            
        Returns:
            True if server started successfully
        """
        try:
            zip_path = game.get("file_path")
            if not zip_path or not os.path.exists(zip_path):
                log(f"[GameRuntime] Game file not found: {zip_path}")
                return False

            # Extract game to temp directory
            temp_dir = tempfile.mkdtemp(prefix=f"game_{room_id}_")
            self.temp_dirs[room_id] = temp_dir
            
            log(f"[GameRuntime] Extracting {zip_path} to {temp_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)

            # Find server entry file
            server_entry = self._find_server_entry(temp_dir, game)
            if not server_entry:
                log(f"[GameRuntime] Could not find server entry file")
                return False

            # Launch game server process
            cmd = [
                sys.executable,
                server_entry,
                "--host", "0.0.0.0",
                "--port", str(port),
            ]
            
            log(f"[GameRuntime] Starting: {' '.join(cmd)}")
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(server_entry),
            )
            
            self.running_servers[room_id] = proc
            log(f"[GameRuntime] Game server started for room {room_id} on port {port}, PID={proc.pid}")
            return True

        except Exception as e:
            log(f"[GameRuntime] Error starting game server: {e}")
            return False

    def _find_server_entry(self, temp_dir: str, game: Dict[str, Any]) -> Optional[str]:
        """Find the server entry file in extracted game directory."""
        # First try the explicit entry from game metadata
        cli_entry = game.get("cli_entry", "")
        if cli_entry:
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f == cli_entry or f.endswith(cli_entry):
                        return os.path.join(root, f)
        
        # Fallback: look for *server*.py
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                if "server" in f.lower() and f.endswith(".py"):
                    return os.path.join(root, f)
        
        return None

    def stop_game_server(self, room_id: str) -> bool:
        """Stop a running game server."""
        if room_id not in self.running_servers:
            return False
        
        try:
            proc = self.running_servers[room_id]
            proc.terminate()
            proc.wait(timeout=5)
        except Exception as e:
            log(f"[GameRuntime] Error stopping server: {e}")
            try:
                proc.kill()
            except:
                pass
        
        del self.running_servers[room_id]
        
        # Clean up temp directory
        if room_id in self.temp_dirs:
            import shutil
            try:
                shutil.rmtree(self.temp_dirs[room_id])
            except:
                pass
            del self.temp_dirs[room_id]
        
        return True

    def cleanup_all(self):
        """Stop all running servers and clean up."""
        for room_id in list(self.running_servers.keys()):
            self.stop_game_server(room_id)
