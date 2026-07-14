import asyncio
import structlog
from typing import Callable, Awaitable
from collectors.base.validation_interface import ValidationInterface
from mdil.schema import RawReading
from validation.validator import ValidationEngine
from normalization.normalizer import NormalizerEngine
from normalization.canonical import CanonicalEvent

logger = structlog.get_logger(__name__)

class PipelineEngine(ValidationInterface):
    """
    Hooks directly into the Collector supervisor.
    Implements the ValidationInterface so it can accept RawReadings directly
    from the asynchronous collectors in real-time.
    
    Routes:
      Collector -> forward -> Validation -> Normalization -> Publisher
    """
    
    def __init__(self, publish_callback: Callable[[CanonicalEvent], Awaitable[None]]):
        self.validator = ValidationEngine()
        self.normalizer = NormalizerEngine()
        self.publish_callback = publish_callback
        self._queue: asyncio.Queue[RawReading] = asyncio.Queue(maxsize=10_000)
        self._running = False
        self._worker_task: asyncio.Task | None = None
        
    async def start(self) -> None:
        self._running = True
        self._worker_task = asyncio.create_task(self._process_loop())
        logger.info("pipeline_engine_started")
        
    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("pipeline_engine_stopped")
        
    async def forward(self, reading: RawReading) -> None:
        """Called by Collectors. Puts reading into the async processing queue."""
        try:
            await self._queue.put(reading)
        except asyncio.QueueFull:
            logger.error("pipeline_queue_full_dropped_reading", device_id=reading.device_id)

    async def _process_loop(self) -> None:
        """Background worker pulling from queue and running the gauntlet."""
        while self._running:
            try:
                reading = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
                
            try:
                await self._process_reading(reading)
            except Exception as e:
                logger.error("pipeline_unhandled_exception", error=str(e), exc_info=True)

    async def _process_reading(self, reading: RawReading) -> None:
        # STEP 1: Validation
        validation_result = self.validator.validate(reading)
        
        # STEP 2: Normalization
        canonical_event, error = self.normalizer.normalize(validation_result)
        
        if not canonical_event:
            # Dropped either by validation (rejected) or normalization (no patient/loinc)
            return
            
        # STEP 3: Publish to downstream (Redis Event Bus)
        await self.publish_callback(canonical_event)
