"""
HELIOS OS + SEVRA AI
Dashboard WebSocket Framework (Section 9 & 10)
"""

import asyncio
import json
import structlog
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
from redis.asyncio import Redis

from dashboard.config import dash_config

logger = structlog.get_logger(__name__)

class WebSocketManager:
    """Manages active WS connections and Redis Pub/Sub integration."""
    
    def __init__(self):
        # map: user_id -> list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # map: channel_name -> set of user_ids listening
        self.channel_subscriptions: Dict[str, set] = {}
        self.redis: Redis = None
        self.pubsub_task: asyncio.Task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a connection and track it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("websocket_connected", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a connection."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from subscriptions if no active connections left
        if user_id not in self.active_connections:
            for channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(user_id)
        
        logger.info("websocket_disconnected", user_id=user_id)

    async def subscribe_user(self, user_id: str, channel: str):
        """Subscribe a user to a specific logical channel (e.g., patient:123:vitals)"""
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(user_id)

    async def start_redis_listener(self):
        """Starts the background task to listen to Redis Pub/Sub."""
        self.redis = Redis.from_url(dash_config.REDIS_URL, decode_responses=True)
        pubsub = self.redis.pubsub()
        
        # Subscribe to all helios dashboard topics using a pattern
        await pubsub.psubscribe("dashboard:channels:*")
        
        logger.info("websocket_redis_listener_started")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    # Extract the logical channel from the redis topic
                    logical_channel = channel.replace("dashboard:channels:", "")
                    data = message["data"]
                    await self._broadcast_to_subscribers(logical_channel, data)
        except Exception as e:
            logger.error("websocket_redis_listener_failed", error=str(e))

    async def _broadcast_to_subscribers(self, channel: str, message: str):
        """Sends a JSON message to all websockets subscribed to the channel."""
        subscribers = self.channel_subscriptions.get(channel, set())
        for user_id in list(subscribers):
            connections = self.active_connections.get(user_id, [])
            for ws in connections:
                try:
                    await ws.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(ws, user_id)
                except Exception as e:
                    logger.warning("websocket_send_failed", user_id=user_id, error=str(e))

ws_manager = WebSocketManager()
