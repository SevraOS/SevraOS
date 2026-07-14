import redis.asyncio as redis
import structlog
from typing import Optional
from eventbus.config import config

logger = structlog.get_logger(__name__)

class RedisClientManager:
    """
    Manages the Async Redis Connection Pool for the Event Bus.
    Implements singleton pattern to share the pool across the app.
    """
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize connection pool."""
        if cls._pool is None:
            cls._pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_POOL_SIZE,
                socket_timeout=config.REDIS_TIMEOUT,
                decode_responses=False # Streams yield bytes natively
            )
            cls._client = redis.Redis(connection_pool=cls._pool)
            logger.info("redis_pool_initialized", url=config.REDIS_URL, size=config.REDIS_POOL_SIZE)

    @classmethod
    async def disconnect(cls) -> None:
        """Close pool gracefully."""
        if cls._client:
            await cls._client.aclose()
            logger.info("redis_pool_closed")
            cls._client = None
            cls._pool = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get the active Redis client. Raises if not connected."""
        if cls._client is None:
            raise RuntimeError("Redis connection pool is not initialized. Call connect() first.")
        return cls._client
        
    @classmethod
    async def is_healthy(cls) -> bool:
        """Check Redis connectivity."""
        if not cls._client:
            return False
        try:
            return await cls._client.ping()
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False
