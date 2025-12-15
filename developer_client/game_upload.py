# path: developer_client/game_upload.py

import os
import socket
import json
import zipfile
from pathlib import Path

from utils.protocol import send_json, recv_json
from utils.file_transfer import encode_chunk

# Developer games directory (under developer_client/)
GAMES_DIR = Path(__file__).resolve().parent / "games"


class GameUploader:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    # ------------------------------------------------------------
    # Helper: Scan games folder
    # ------------------------------------------------------------
    def scan_games_folder(self) -> list[Path]:
        """Scan ./games folder for available game directories."""
        if not GAMES_DIR.exists():
            return []
        return [p for p in GAMES_DIR.iterdir() if p.is_dir() and not p.name.startswith('.')]

    def choose_existing_game(self) -> Path | None:
        """Let developer select from existing game folders."""
        games = self.scan_games_folder()
        
        if not games:
            print(f"(No game folders found in {GAMES_DIR})")
            return None
        
        print(f"\n=== Available Games in {GAMES_DIR} ===")
        for idx, g in enumerate(games, start=1):
            # List some files to help identify
            files = [f.name for f in g.iterdir() if f.is_file() and f.suffix == '.py'][:3]
            print(f"{idx}. {g.name}/  (files: {', '.join(files)}...)")
        
        print(f"{len(games) + 1}. Enter custom path")
        
        choice = input("\nSelect folder number: ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice)
        
        if idx == len(games) + 1:
            # Custom path
            custom = input("Enter full path: ").strip()
            return Path(custom) if custom else None
        
        if 1 <= idx <= len(games):
            return games[idx - 1]
        return None

    # ------------------------------------------------------------
    # Step 1 — Developer fills fields in terminal
    # ------------------------------------------------------------
    def input_game_metadata(self, folder: Path = None) -> dict | None:
        print("\n=== Upload New Game ===")

        name = input("Game Name: ").strip()
        version = input("Version (e.g., 1.0.0): ").strip()
        description = input("Description: ").strip()

        # Auto-detect entry files if folder is provided
        server_entry = ""
        client_entry = ""
        
        if folder:
            py_files = [f.name for f in folder.iterdir() if f.suffix == '.py']
            server_files = [f for f in py_files if 'server' in f.lower()]
            client_files = [f for f in py_files if 'client' in f.lower()]
            
            if server_files:
                print(f"\nDetected server files: {server_files}")
                server_entry = server_files[0]
            if client_files:
                print(f"Detected client files: {client_files}")
                client_entry = client_files[0]

        print("\n[Entry Files]")
        server_input = input(f"Server Entry [{server_entry}]: ").strip()
        server_entry = server_input if server_input else server_entry
        
        client_input = input(f"Client Entry [{client_entry}]: ").strip()
        client_entry = client_input if client_input else client_entry

        # Max players (for multiplayer games)
        max_players_input = input("Max Players (default 2): ").strip()
        max_players = int(max_players_input) if max_players_input.isdigit() else 2
        max_players = max(2, min(max_players, 8))  # Clamp between 2-8

        if not all([name, version, description, server_entry, client_entry]):
            print("❌ All fields are required.")
            return None

        return {
            "name": name,
            "version": version,
            "description": description,
            "server_entry": server_entry,
            "client_entry": client_entry,
            "max_players": max_players,
        }

    # ------------------------------------------------------------
    # Step 2 — Ask for game folder & validate it
    # ------------------------------------------------------------
    def choose_game_folder(self, info: dict) -> Path | None:
        print("\nGame Folder Path (must contain the entry files):")
        folder = Path(input("Path: ").strip())

        if not folder.exists() or not folder.is_dir():
            print("❌ Folder does not exist.")
            return None

        server_path = folder / info["server_entry"]
        client_path = folder / info["client_entry"]

        if not server_path.exists():
            print(f"❌ Missing server_entry in folder: {server_path}")
            return None
        if not client_path.exists():
            print(f"❌ Missing client_entry in folder: {client_path}")
            return None

        print("✅ Folder validated.")
        return folder
    
    def validate_folder(self, folder: Path, info: dict) -> bool:
        """Validate that folder contains required entry files."""
        server_path = folder / info["server_entry"]
        client_path = folder / info["client_entry"]

        if not server_path.exists():
            print(f"❌ Missing server entry: {server_path}")
            return False
        if not client_path.exists():
            print(f"❌ Missing client entry: {client_path}")
            return False

        print("✅ Folder validated.")
        return True

    # ------------------------------------------------------------
    # Step 3 — Create zip file
    # ------------------------------------------------------------
    def create_zip(self, folder: Path, info: dict) -> Path:
        zip_name = f"{info['name']}_{info['version']}.zip"
        zip_path = folder.parent / zip_name

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # add game files
            for root, dirs, files in os.walk(folder):
                for f in files:
                    full = Path(root) / f
                    rel = full.relative_to(folder)
                    zf.write(full, rel)

            # embed game_info.json inside the zip
            zf.writestr("game_info.json", json.dumps(info, indent=2))

        print(f"📦 Packaged game → {zip_path}")
        return zip_path

    # ------------------------------------------------------------
    # Step 4 — Upload via chunk protocol
    # ------------------------------------------------------------
    def upload_game(self):
        # First, let user select game folder
        print("\n=== Select Game Folder ===")
        folder = self.choose_existing_game()
        
        if not folder:
            return
        
        if not folder.exists() or not folder.is_dir():
            print(f"❌ Invalid folder: {folder}")
            return
        
        print(f"\nSelected: {folder}")
        
        # Get metadata with auto-detection
        info = self.input_game_metadata(folder)
        if not info:
            return

        # Validate the folder has required files
        if not self.validate_folder(folder, info):
            return

        zip_path = self.create_zip(folder, info)

        # 1. Start upload session
        send_json(self.sock, {
            "action": "upload_game_init",
            "name": info["name"],
            "version": info["version"],
            "description": info["description"],
            "cli_entry": info["client_entry"],
            "gui_entry": info["server_entry"],
            "max_players": info.get("max_players", 2),
        })

        resp = recv_json(self.sock)
        if resp.get("status") != "ok":
            print(f"❌ Upload init failed: {resp.get('message', 'Unknown error')}")
            return

        upload_id = resp["upload_id"]
        chunk_size = resp["chunk_size"]

        print(f"🚀 Uploading with upload_id={upload_id[:8]}..., chunk_size={chunk_size}")

        # 2. Stream chunks
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                eof = not chunk or len(chunk) < chunk_size
                
                send_json(self.sock, {
                    "action": "upload_game_chunk",
                    "upload_id": upload_id,
                    "data": encode_chunk(chunk if chunk else b""),
                    "eof": eof,
                })

                resp = recv_json(self.sock)
                if resp.get("status") != "ok":
                    print(f"❌ Upload failed: {resp.get('message', 'Unknown error')}")
                    return
                
                if eof:
                    break

        print("🎉 Game uploaded successfully!")
        zip_path.unlink()  # remove temp zip

    def update_game(self, existing_game: dict):
        """Update an existing game with new version."""
        print(f"\n=== Updating: {existing_game['name']} ===")
        print(f"Current version: {existing_game['version']}")
        
        # Select new game folder
        print("\nSelect the folder with updated game files:")
        folder = self.choose_existing_game()
        
        if not folder:
            return
        
        if not folder.exists() or not folder.is_dir():
            print(f"❌ Invalid folder: {folder}")
            return
        
        print(f"\nSelected: {folder}")
        
        # Get metadata for update - pre-fill from existing game
        info = self._input_update_metadata(folder, existing_game)
        if not info:
            return

        # Validate the folder has required files
        if not self.validate_folder(folder, info):
            return

        zip_path = self.create_zip(folder, info)

        # Start upload session with game_id for update
        send_json(self.sock, {
            "action": "upload_game_init",
            "game_id": existing_game["game_id"],  # Include game_id for update
            "name": info["name"],  # Keep same name
            "version": info["version"],
            "description": info["description"],
            "cli_entry": info["client_entry"],
            "gui_entry": info["server_entry"],
            "max_players": info.get("max_players", 2),
        })

        resp = recv_json(self.sock)
        if resp.get("status") != "ok":
            print(f"❌ Upload init failed: {resp.get('message', 'Unknown error')}")
            return

        upload_id = resp["upload_id"]
        chunk_size = resp["chunk_size"]

        print(f"🚀 Uploading update with upload_id={upload_id[:8]}...")

        # Stream chunks
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                eof = not chunk or len(chunk) < chunk_size
                
                send_json(self.sock, {
                    "action": "upload_game_chunk",
                    "upload_id": upload_id,
                    "data": encode_chunk(chunk if chunk else b""),
                    "eof": eof,
                })

                resp = recv_json(self.sock)
                if resp.get("status") != "ok":
                    print(f"❌ Upload failed: {resp.get('message', 'Unknown error')}")
                    return
                
                if eof:
                    break

        print(f"🎉 Game updated to version {info['version']}!")
        zip_path.unlink()

    def _input_update_metadata(self, folder: Path, existing: dict) -> dict | None:
        """Get metadata for game update - pre-fills from existing game."""
        print("\n[Update Metadata]")
        print(f"Game Name: {existing['name']} (cannot change)")
        
        # Version is required to change
        current_ver = existing['version']
        version = input(f"New Version (current: {current_ver}): ").strip()
        if not version:
            print("❌ Version is required for update.")
            return None
        if version == current_ver:
            print("⚠️  Warning: Version is the same as current.")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                return None
        
        # Description - optional, show current
        current_desc = existing.get('description', '')
        print(f"Current description: {current_desc[:50]}...")
        desc_input = input("New Description (Enter to keep current): ").strip()
        description = desc_input if desc_input else current_desc

        # Auto-detect entry files
        py_files = [f.name for f in folder.iterdir() if f.suffix == '.py']
        server_files = [f for f in py_files if 'server' in f.lower()]
        client_files = [f for f in py_files if 'client' in f.lower()]
        
        server_entry = server_files[0] if server_files else existing.get('gui_entry', '')
        client_entry = client_files[0] if client_files else existing.get('cli_entry', '')

        print(f"\nDetected server: {server_entry}")
        print(f"Detected client: {client_entry}")
        
        server_input = input(f"Server Entry [{server_entry}]: ").strip()
        server_entry = server_input if server_input else server_entry
        
        client_input = input(f"Client Entry [{client_entry}]: ").strip()
        client_entry = client_input if client_input else client_entry

        # Max players
        current_max = existing.get('max_players', 2)
        max_input = input(f"Max Players [{current_max}]: ").strip()
        max_players = int(max_input) if max_input.isdigit() else current_max
        max_players = max(2, min(max_players, 8))

        return {
            "name": existing['name'],  # Keep same name
            "version": version,
            "description": description,
            "server_entry": server_entry,
            "client_entry": client_entry,
            "max_players": max_players,
        }
