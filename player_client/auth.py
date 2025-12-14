# path: player_client/auth.py
from typing import Optional
from utils.protocol import send_json, recv_json
import socket


class PlayerAuth:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.username: Optional[str] = None

    def register(self) -> bool:
        print("\n=== Player Registration ===")
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        if not username or not password:
            print("❌ Username and password cannot be empty")
            return False

        send_json(self.sock, {
            "action": "register",
            "role": "player",
            "username": username,
            "password": password
        })
        resp = recv_json(self.sock)

        if resp and resp.get("status") == "ok":
            print("✅ Registration successful! Please login.")
            return True
        else:
            print(f"❌ Registration failed: {resp.get('message', 'Unknown error')}")
            return False

    def login(self) -> bool:
        print("\n=== Player Login ===")
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        send_json(self.sock, {
            "action": "login",
            "role": "player",
            "username": username,
            "password": password
        })
        resp = recv_json(self.sock)

        if resp and resp.get("status") == "ok":
            self.username = username
            print(f"✅ Login successful! Welcome {username}")
            return True
        else:
            print(f"❌ Login failed: {resp.get('message', 'Unknown error')}")
            return False
