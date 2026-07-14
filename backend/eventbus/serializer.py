import json
import msgpack
from typing import Any, Dict
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

class EventSerializer:
    """
    Handles serialization of Canonical schemas into bytes for Redis Streams.
    Supports both JSON and MessagePack.
    """
    
    @staticmethod
    def to_bytes(event: BaseModel, use_msgpack: bool = False) -> bytes:
        """Serialize a Pydantic event to bytes."""
        # Convert to dict with ISO timestamps
        event_dict = event.model_dump(mode="json")
        
        if use_msgpack:
            return msgpack.packb(event_dict, use_bin_type=True)
        else:
            return json.dumps(event_dict).encode("utf-8")

    @staticmethod
    def from_bytes(data: bytes, is_msgpack: bool = False) -> Dict[str, Any]:
        """Deserialize bytes from Redis back to a dictionary."""
        try:
            if is_msgpack:
                return msgpack.unpackb(data, raw=False)
            else:
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error("deserialization_failed", error=str(e), is_msgpack=is_msgpack)
            raise ValueError(f"Failed to deserialize event: {e}")
