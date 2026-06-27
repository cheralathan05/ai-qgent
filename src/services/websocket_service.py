"""
APA-OS Device WebSocket Manager
Handles real-time communication between the backend and the device/frontend
"""

import asyncio
import logging
import json
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class DeviceWebSocketManager:
    def __init__(self):
        # Mapping of user_id to set of active websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new websocket connection"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove websocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections of a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message to user {user_id}: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected users"""
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)

manager = DeviceWebSocketManager()

def get_websocket_manager():
    return manager
