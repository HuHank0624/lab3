# path: developer_client/auth.py
from typing import Optional, Dict
from utils.protocol import send_json, recv_json
import socket


class DeveloperAuth:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.username = None

    def register(self):
        print("\n=== Developer Registration ===")
        username = input("New username: ").strip()
        password = input("Password: ").strip()

        send_json(self.sock, {
            "action": "register",
            "role": "developer",
            "username": username,
            "password": password
        })
        resp = recv_json(self.sock)

        if resp and resp.get("status") == "ok":
            print("✅ Registration successful! Please login.")
        else:
            print(f"❌ Registration failed: {resp.get('message', 'Unknown error')}")

    def login(self) -> bool:
        print("\n=== Developer Login ===")
        username = input("Username: ").strip()
        password = input("Password: ").strip()

        send_json(self.sock, {
            "action": "login",
            "role": "developer",
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
