import asyncio
import structlog
from typing import Optional
from eventbus.client import RedisClientManager
from eventbus.streams import StreamTopic, ConsumerGroup
from eventbus.dead_letter import DeadLetterQueue
from eventbus.config import config

logger = structlog.get_logger(__name__)

class ReplayFramework:
    """
    Handles replaying messages from DLQ or from a specific Stream position.
    """
    
    @staticmethod
    async def replay_dlq(group_name: Optional[str] = None) -> int:
        """
        Reads messages from the DLQ, and republishes them to their original stream.
        If group_name is provided, only replays messages that failed for that group.
        Returns the number of messages replayed.
        """
        client = RedisClientManager.get_client()
        replayed_count = 0
        
        try:
            # Read all from DLQ (0-0)
            messages = await client.xrange(config.DLQ_STREAM_NAME, min='-', max='+')
            
            for msg_id, data in messages:
                dlq_group = data.get(b"consumer_group", b"").decode()
                original_stream = data.get(b"original_stream", b"").decode()
                payload = data.get(b"payload")
                
                if group_name and dlq_group != group_name:
                    continue
                    
                if original_stream and payload:
                    # Republish
                    await client.xadd(original_stream, {"payload": payload})
                    # Remove from DLQ
                    await client.xdel(config.DLQ_STREAM_NAME, msg_id)
                    replayed_count += 1
                    
            logger.info("dlq_replay_completed", count=replayed_count, filter_group=group_name)
            return replayed_count
            
        except Exception as e:
            logger.error("dlq_replay_failed", error=str(e))
            return replayed_count

    @staticmethod
    async def reset_consumer_group(stream: str, group_name: str, start_id: str = "0"):
        """
        Resets a consumer group to a specific ID (or 0 for beginning).
        Allows full replay of a stream for a specific group.
        """
        client = RedisClientManager.get_client()
        try:
            await client.xgroup_setid(stream, group_name, start_id)
            logger.info("consumer_group_reset", stream=stream, group=group_name, start_id=start_id)
        except Exception as e:
            logger.error("consumer_group_reset_failed", error=str(e))
