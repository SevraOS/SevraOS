import asyncio
import structlog
from typing import Callable, Awaitable, Any
from eventbus.config import config

logger = structlog.get_logger(__name__)

class RetryPolicy:
    """
    Executes a coroutine with exponential backoff.
    Used by consumers when processing an event fails transiently (e.g. DB down).
    """
    
    @staticmethod
    async def execute(func: Callable[[], Awaitable[Any]], message_id: str) -> Any:
        attempts = 0
        while attempts < config.RETRY_MAX_ATTEMPTS:
            try:
                return await func()
            except Exception as e:
                attempts += 1
                if attempts >= config.RETRY_MAX_ATTEMPTS:
                    logger.error("max_retries_exhausted", message_id=message_id, error=str(e))
                    raise e
                    
                # Exponential backoff: 1s, 2s, 4s...
                delay = config.RETRY_BASE_DELAY * (2 ** (attempts - 1))
                logger.warning(
                    "processing_failed_retrying", 
                    message_id=message_id, 
                    attempt=attempts, 
                    delay=delay, 
                    error=str(e)
                )
                await asyncio.sleep(delay)
