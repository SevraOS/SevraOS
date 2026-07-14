import structlog
from typing import Optional, Callable, Awaitable
from eventbus.consumer import ConsumerWorker
from eventbus.streams import StreamTopic, ConsumerGroup
from eventbus.serializer import EventSerializer
from eventbus.idempotency import IdempotencyService
from eventbus.schemas import BaseEvent

logger = structlog.get_logger(__name__)

class BaseServiceConsumer:
    """Base class for domain-specific consumers."""
    
    def __init__(self, stream: str, group: str, consumer_name: str):
        self.stream = stream
        self.group = group
        self.idempotency = IdempotencyService()
        self.worker = ConsumerWorker(
            stream=stream,
            group_name=group,
            consumer_name=consumer_name,
            process_func=self._process_wrapper
        )
        # To be overridden by subclasses
        self.handler: Optional[Callable[[BaseEvent], Awaitable[None]]] = None

    async def start(self):
        await self.worker.start()

    async def stop(self):
        await self.worker.stop()

    async def _process_wrapper(self, message_id: str, payload: bytes) -> None:
        if not self.handler:
            return
            
        # 1. Deserialize
        event_dict = EventSerializer.from_bytes(payload)
        event = BaseEvent(**event_dict) # BaseEvent just for ID extraction
        
        # 2. Idempotency Check
        if not await self.idempotency.acquire_lock(event.event_id, self.group):
            # Already processed, skip safely
            return
            
        try:
            # 3. Route to actual handler
            await self.handler(event_dict)
        except Exception as e:
            # Release lock so it can be retried by the RetryPolicy
            await self.idempotency.release_lock(event.event_id, self.group)
            raise e

# --- Specific Consumer Groups ---

class DatabaseConsumer(BaseServiceConsumer):
    def __init__(self, consumer_name: str = "db_worker_1"):
        super().__init__(StreamTopic.VITALS, ConsumerGroup.DATABASE_GROUP, consumer_name)
        
    def bind_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

class AIConsumer(BaseServiceConsumer):
    def __init__(self, consumer_name: str = "ai_worker_1"):
        super().__init__(StreamTopic.VITALS, ConsumerGroup.AI_GROUP, consumer_name)

    def bind_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

class NotificationConsumer(BaseServiceConsumer):
    def __init__(self, consumer_name: str = "notif_worker_1"):
        super().__init__(StreamTopic.ALERTS, ConsumerGroup.NOTIFICATION_GROUP, consumer_name)

    def bind_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

class HospitalSyncConsumer(BaseServiceConsumer):
    def __init__(self, consumer_name: str = "sync_worker_1"):
        super().__init__(StreamTopic.HOSPITAL, ConsumerGroup.HOSPITAL_GROUP, consumer_name)

    def bind_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

class AuditConsumer(BaseServiceConsumer):
    def __init__(self, consumer_name: str = "audit_worker_1"):
        super().__init__(StreamTopic.AUDIT, ConsumerGroup.AUDIT_GROUP, consumer_name)

    def bind_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler
