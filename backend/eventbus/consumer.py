import asyncio
import structlog
from typing import Callable, Awaitable, Dict, Any, Optional
from redis.exceptions import ResponseError
from eventbus.client import RedisClientManager
from eventbus.dead_letter import DeadLetterQueue
from eventbus.retry import RetryPolicy
from eventbus.metrics import metrics

logger = structlog.get_logger(__name__)

class ConsumerWorker:
    """
    Generic worker that binds to a Redis Stream Consumer Group.
    Pulls messages using XREADGROUP, processes them, handles idempotency,
    and acknowledges them (XACK). Moves failures to DLQ.
    """
    
    def __init__(
        self, 
        stream: str, 
        group_name: str, 
        consumer_name: str,
        process_func: Callable[[str, bytes], Awaitable[None]]
    ):
        self.stream = stream
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.process_func = process_func
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def _ensure_group(self):
        """Create consumer group if it doesn't exist."""
        client = RedisClientManager.get_client()
        try:
            # Use '0' to read from the beginning of the stream (handles historical backlog)
            await client.xgroup_create(self.stream, self.group_name, id='0', mkstream=True)
            logger.info("consumer_group_created", stream=self.stream, group=self.group_name)
        except ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" not in str(e):
                raise e

    async def start(self) -> None:
        self._running = True
        await self._ensure_group()
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("consumer_started", consumer=self.consumer_name, group=self.group_name)
        
    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("consumer_stopped", consumer=self.consumer_name)

    async def _consume_loop(self) -> None:
        client = RedisClientManager.get_client()
        
        while self._running:
            try:
                # Block for 2 seconds waiting for new messages ('>')
                # Returns: [[b'stream_name', [(b'msg_id', {b'key': b'val'})]]]
                streams = await client.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream: '>'},
                    count=10
                )
                
                if not streams:
                    await asyncio.sleep(0.1)
                    continue
                    
                for stream_name, messages in streams:
                    for message_id, message_data in messages:
                        msg_id_str = message_id.decode()
                        payload = message_data.get(b"payload")
                        
                        if not payload:
                            # Invalid message format
                            await client.xack(self.stream, self.group_name, message_id)
                            continue
                            
                        await self._handle_message(msg_id_str, payload)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("consumer_loop_error", error=str(e), exc_info=True)
                await asyncio.sleep(1.0)
                
    async def _handle_message(self, message_id: str, payload: bytes) -> None:
        """Process a single message with retries and DLQ routing."""
        client = RedisClientManager.get_client()
        
        try:
            # Wrap processing in exponential backoff
            await RetryPolicy.execute(
                lambda: self.process_func(message_id, payload),
                message_id
            )
            
            # Successfully processed, acknowledge
            await client.xack(self.stream, self.group_name, message_id)
            metrics.inc_consumed(self.group_name)
            
        except Exception as e:
            # Max retries exhausted. Send to Dead Letter Queue
            metrics.inc_error(self.group_name)
            await DeadLetterQueue.send_to_dlq(
                stream=self.stream,
                group=self.group_name,
                message_id=message_id,
                payload=payload,
                reason=str(e)
            )
