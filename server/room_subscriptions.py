# path: server/room_subscriptions.py
"""
RoomSubscriptionManager - Manages room subscriptions for real-time updates.
"""
import socket
import threading
from typing import Dict, Set, Any, Optional
from utils.protocol import send_json
from .utils import log


class RoomSubscriptionManager:
    """Manages client subscriptions to room updates for real-time notifications."""

    def __init__(self):
        # room_id -> set of (socket, username)
        self.subscriptions: Dict[str, Set[tuple]] = {}
        self.lock = threading.RLock()
        # socket -> (room_id, username) for quick lookup
        self.socket_to_room: Dict[socket.socket, tuple] = {}

    def subscribe(self, room_id: str, sock: socket.socket, username: str) -> None:
        """Subscribe a client to room updates."""
        with self.lock:
            # Unsubscribe from any previous room
            self.unsubscribe(sock)
            
            if room_id not in self.subscriptions:
                self.subscriptions[room_id] = set()
            self.subscriptions[room_id].add((sock, username))
            self.socket_to_room[sock] = (room_id, username)
            log(f"[Subscriptions] {username} subscribed to room {room_id[:8]}...")

    def unsubscribe(self, sock: socket.socket) -> None:
        """Unsubscribe a client from their current room."""
        with self.lock:
            if sock in self.socket_to_room:
                room_id, username = self.socket_to_room[sock]
                if room_id in self.subscriptions:
                    self.subscriptions[room_id].discard((sock, username))
                    if not self.subscriptions[room_id]:
                        del self.subscriptions[room_id]
                del self.socket_to_room[sock]
                log(f"[Subscriptions] {username} unsubscribed from room {room_id[:8]}...")

    def broadcast_room_update(self, room_id: str, room_info: Dict[str, Any], 
                              exclude_sock: Optional[socket.socket] = None) -> None:
        """Broadcast room update to all subscribed clients except the sender."""
        with self.lock:
            if room_id not in self.subscriptions:
                return
            
            subscribers = list(self.subscriptions[room_id])
        
        # Send outside lock to avoid deadlocks
        message = {
            "type": "room_update",
            "room": room_info,
        }
        
        dead_sockets = []
        for sock, username in subscribers:
            if sock == exclude_sock:
                continue
            try:
                send_json(sock, message)
            except Exception as e:
                log(f"[Subscriptions] Failed to send to {username}: {e}")
                dead_sockets.append(sock)
        
        # Clean up dead sockets
        for sock in dead_sockets:
            self.unsubscribe(sock)

    def broadcast_game_started(self, room_id: str, room_info: Dict[str, Any]) -> None:
        """Broadcast game started notification to all subscribed clients."""
        with self.lock:
            if room_id not in self.subscriptions:
                return
            
            subscribers = list(self.subscriptions[room_id])
        
        message = {
            "type": "game_started",
            "room": room_info,
            "game_port": room_info.get("game_port"),
        }
        
        dead_sockets = []
        for sock, username in subscribers:
            try:
                send_json(sock, message)
            except Exception as e:
                log(f"[Subscriptions] Failed to send game_started to {username}: {e}")
                dead_sockets.append(sock)
        
        for sock in dead_sockets:
            self.unsubscribe(sock)

    def get_subscribers(self, room_id: str) -> list:
        """Get list of subscribers for a room."""
        with self.lock:
            return list(self.subscriptions.get(room_id, []))
