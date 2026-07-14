import structlog
from typing import Optional
from eventbus.client import RedisClientManager

logger = structlog.get_logger(__name__)

class IdempotencyService:
    """
    Prevents duplicate processing of the same event by different consumer replicas.
    Uses Redis SETNX (Set if Not Exists) with a TTL.
    """
    
    def __init__(self, prefix: str = "idemp:", ttl_seconds: int = 86400):
        self.prefix = prefix
        self.ttl = ttl_seconds
        
    async def acquire_lock(self, event_id: str, consumer_group: str) -> bool:
        """
        Attempt to acquire an idempotency lock for this event and group.
        Returns True if acquired (safe to process).
        Returns False if already processed.
        """
        client = RedisClientManager.get_client()
        key = f"{self.prefix}{consumer_group}:{event_id}"
        
        # setnx returns True if the key was set, False if it already existed
        acquired = await client.set(key, "1", nx=True, ex=self.ttl)
        
        if not acquired:
            logger.debug("idempotency_lock_denied", event_id=event_id, group=consumer_group)
            
        return bool(acquired)
        
    async def release_lock(self, event_id: str, consumer_group: str) -> None:
        """
        Releases the lock if processing failed so it can be retried.
        """
        client = RedisClientManager.get_client()
        key = f"{self.prefix}{consumer_group}:{event_id}"
        await client.delete(key)
        logger.debug("idempotency_lock_released", event_id=event_id, group=consumer_group)
