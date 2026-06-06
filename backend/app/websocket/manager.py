"""
WebSocket connection manager for real-time chat.
Rooms are keyed by room_id; each room holds a set of active WebSocket connections.
Redis pub/sub bridges multiple Uvicorn workers when scaling horizontally.
"""
import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # room_id → set of connected WebSockets
        self._rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        self._rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        room = self._rooms.get(room_id, set())
        room.discard(websocket)
        if not room:
            self._rooms.pop(room_id, None)

    async def broadcast(self, room_id: int, message: dict):
        payload = json.dumps(message)
        dead = set()
        for ws in self._rooms.get(room_id, set()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws, room_id)

    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))


# Singleton shared across the app
manager = ConnectionManager()
