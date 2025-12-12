# path: developer_client/game_upload.py

import os
import socket
import json
import zipfile
from pathlib import Path

from utils.protocol import send_json, recv_json
from utils.file_transfer import encode_chunk



class GameUploader:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    # ------------------------------------------------------------
    # Step 1 — Developer fills fields in terminal
    # ------------------------------------------------------------
    def input_game_metadata(self) -> dict | None:
        print("\n=== Upload New Game ===")

        name = input("Game Name: ").strip()
        version = input("Version: ").strip()
        description = input("Description: ").strip()

        server_entry = input("Server Entry (e.g., gomoku_server.py): ").strip()
        client_entry = input("Client Entry (e.g., gomoku_client.py): ").strip()

        if not all([name, version, description, server_entry, client_entry]):
            print("❌ All fields are required.")
            return None

        return {
            "name": name,
            "version": version,
            "description": description,
            "server_entry": server_entry,
            "client_entry": client_entry,
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
        info = self.input_game_metadata()
        if not info:
            return

        folder = self.choose_game_folder(info)
        if not folder:
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
        })

        resp = recv_json(self.sock)
        if resp.get("status") != "ok":
            print("❌ Upload init failed:", resp)
            return

        upload_id = resp["upload_id"]
        chunk_size = resp["chunk_size"]

        print(f"🚀 Uploading with upload_id={upload_id}, chunk_size={chunk_size}")

        # 2. Stream chunks
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    # send final EOF chunk
                    send_json(self.sock, {
                        "action": "upload_game_chunk",
                        "upload_id": upload_id,
                        "data": encode_chunk(b""),
                        "eof": True,
                    })
                    break

                send_json(self.sock, {
                    "action": "upload_game_chunk",
                    "upload_id": upload_id,
                    "data": encode_chunk(chunk),
                    "eof": False,
                })

                resp = recv_json(self.sock)
                if resp.get("status") != "ok":
                    print("❌ Upload failed:", resp)
                    return

        print("🎉 Game uploaded successfully!")
        zip_path.unlink()  # remove temp zip
