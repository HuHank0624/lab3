# path: developer_client/game_manage.py
import socket
from utils.protocol import send_json, recv_json


class GameManagerClient:
    def __init__(self, sock: socket.socket, username: str):
        self.sock = sock
        self.username = username

    def list_my_games(self):
        send_json(self.sock, {"action": "list_games"})
        resp = recv_json(self.sock)

        if resp.get("status") != "ok":
            print("❌ Failed:", resp)
            return

        print("\n=== Your Uploaded Games ===")
        for g in resp["games"]:
            if g["developer"] == self.username:
                print(f"- {g['name']} (id={g['game_id']}) version={g['version']}")
        print("")

    def update_game(self):
        print("\n=== Update Game ===")
        self.list_my_games()

        game_id = input("Enter game_id to update: ").strip()
        version = input("New version: ").strip()
        description = input("New description: ").strip()
        zip_path = input("Path to updated .zip: ").strip()
        cli_entry = input("CLI entry: ").strip()
        gui_entry = input("GUI entry: ").strip()

        # Reuse upload logic
        from .game_upload import GameUploader
        uploader = GameUploader(self.sock, self.username)
        print("Note: Updating game uses same upload flow as new upload.")
        uploader.upload_game()

    def delete_game(self):
        print("\n=== Delete (Deactivate) Game ===")
        print("❗ HW3 通常不要求完全刪除遊戲，僅做 active flag 設定即可")
        print("❗ 因 server 尚未實作 delete_game，所以這裡先保留")
