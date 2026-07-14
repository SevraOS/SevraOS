import json
import structlog
from datetime import datetime, timezone
from eventbus.client import RedisClientManager
from eventbus.config import config
from eventbus.metrics import metrics

logger = structlog.get_logger(__name__)

class DeadLetterQueue:
    """
    Manages failed events.
    Moves messages that fail processing multiple times into a DLQ Stream.
    """
    
    @classmethod
    async def send_to_dlq(cls, stream: str, group: str, message_id: str, payload: bytes, reason: str):
        """Move a failed message to the DLQ stream."""
        client = RedisClientManager.get_client()
        
        dlq_event = {
            "original_stream": stream,
            "consumer_group": group,
            "original_message_id": message_id,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "payload": payload
        }
        
        try:
            await client.xadd(config.DLQ_STREAM_NAME, dlq_event)
            metrics.inc_dlq()
            logger.error("message_moved_to_dlq", original_id=message_id, stream=stream, group=group)
            
            # Acknowledge the original message so it doesn't stay in PEL
            await client.xack(stream, group, message_id)
            
        except Exception as e:
            logger.critical("dlq_insertion_failed", error=str(e), original_id=message_id)
