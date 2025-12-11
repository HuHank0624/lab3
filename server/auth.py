# path: server/auth.py
from typing import Dict, Any, Optional

from .data import DataStore
from .utils import log


class AuthManager:
    """Handle registration, login, and session bookkeeping."""

    def __init__(self, datastore: DataStore):
        self.datastore = datastore
        # Maps conn_id (id(sock)) -> session info
        self.sessions: Dict[int, Dict[str, Any]] = {}

    def register(self, username: str, password: str, role: str) -> Dict[str, Any]:
        ok = self.datastore.register_user(username, password, role)
        if not ok:
            return {"status": "error", "message": "Username already exists"}
        return {"status": "ok", "message": "Registration successful"}

    def login(
        self, conn_id: int, username: str, password: str, role: str
    ) -> Dict[str, Any]:
        if not self.datastore.validate_login(username, password, role):
            return {"status": "error", "message": "Invalid credentials"}
        # Only one session per username is enforced by overwriting
        self.sessions[conn_id] = {"username": username, "role": role}
        log(f"User logged in: {username} ({role}) conn_id={conn_id}")
        return {"status": "ok", "message": "Login successful", "username": username, "role": role}

    def logout(self, conn_id: int) -> None:
        sess = self.sessions.pop(conn_id, None)
        if sess:
            log(f"User logged out: {sess['username']} ({sess['role']})")

    def get_session(self, conn_id: int) -> Optional[Dict[str, Any]]:
        return self.sessions.get(conn_id)

    def require_login(self, conn_id: int) -> Optional[Dict[str, Any]]:
        sess = self.get_session(conn_id)
        return sess
