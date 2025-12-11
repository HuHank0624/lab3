# path: developer_client/game_upload.py
import os
import socket
from typing import Dict, Any
from .utils import send_json, recv_json, encode_chunk


class GameUploader:
    def __init__(self, sock: socket.socket, developer: str):
        self.sock = sock
        self.developer = developer

    def upload_game(self):
        print("\n=== Upload New Game ===")
        name = input("Game name: ").strip()
        version = input("Version: ").strip()
        description = input("Description: ").strip()
        zip_path = input("Path to .zip file: ").strip()
        cli_entry = input("CLI entry (e.g., main.py): ").strip()
        gui_entry = input("GUI entry (optional, or leave blank): ").strip()

        if not os.path.exists(zip_path):
            print("❌ File does not exist.")
            return

        # Request upload session
        send_json(self.sock, {
            "action": "upload_game_init",
            "name": name,
            "version": version,
            "description": description,
            "cli_entry": cli_entry,
            "gui_entry": gui_entry
        })
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print("❌ Upload init failed:", resp)
            return

        upload_id = resp["upload_id"]
        chunk_size = resp["chunk_size"]

        print(f"Upload session started: {upload_id}")
        print(f"Chunk size: {chunk_size}")

        with open(zip_path, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    # Send empty chunk with eof
                    send_json(self.sock, {
                        "action": "upload_game_chunk",
                        "upload_id": upload_id,
                        "data": encode_chunk(b""),
                        "eof": True
                    })
                    break

                send_json(self.sock, {
                    "action": "upload_game_chunk",
                    "upload_id": upload_id,
                    "data": encode_chunk(data),
                    "eof": False
                })

                resp = recv_json(self.sock)
                if resp.get("status") != "ok":
                    print("❌ Upload error:", resp)
                    return

        print("✅ Upload completed successfully!")
