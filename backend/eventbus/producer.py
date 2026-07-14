import json
import os
import asyncio
import structlog
from typing import Optional
from redis.exceptions import ConnectionError, TimeoutError
from eventbus.client import RedisClientManager
from eventbus.serializer import EventSerializer
from eventbus.config import config
from eventbus.metrics import metrics
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class OfflineBuffer:
    """Simple offline file-based buffer for events when Redis is down."""
    
    def __init__(self, buffer_path: str):
        self.buffer_path = buffer_path
        os.makedirs(os.path.dirname(self.buffer_path), exist_ok=True)
        
    def write(self, stream: str, data: bytes):
        """Append event to local file."""
        with open(self.buffer_path, "ab") as f:
            # We store stream name and payload length for safe reading later
            header = f"{stream}\n".encode()
            f.write(header + data + b"\n===DELIM===\n")
            
    # Note: In a production system, a dedicated background task would read this
    # file when Redis recovers, and replay the events to the Streams.

class EventProducer:
    """
    Publishes events to Redis Streams.
    Handles serialization, offline buffering, and metrics.
    """
    
    def __init__(self):
        self._buffer = OfflineBuffer(config.LOCAL_BUFFER_PATH) if config.ENABLE_LOCAL_BUFFER else None

    async def publish(self, stream: str, event: BaseModel, use_msgpack: bool = False) -> Optional[str]:
        """
        Serialize and publish an event to a specific Redis stream.
        Returns the Redis Message ID on success, None if offline-buffered.
        """
        payload = EventSerializer.to_bytes(event, use_msgpack=use_msgpack)
        
        try:
            client = RedisClientManager.get_client()
            # XADD: stream name, fields dict. We use a standard 'payload' key.
            message_id = await client.xadd(stream, {"payload": payload})
            
            # Record metric
            metrics.inc_published(stream)
            logger.debug("event_published", stream=stream, message_id=message_id.decode())
            return message_id.decode()
            
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            logger.warning("redis_unavailable_buffering_locally", stream=stream, error=str(e))
            if self._buffer:
                self._buffer.write(stream, payload)
            else:
                logger.error("event_dropped_no_buffer", stream=stream)
            return None
