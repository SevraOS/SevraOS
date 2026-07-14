"""
HELIOS OS + SEVRA AI
Database Consumer - SECTION 7
"""

import structlog
from typing import Dict, Any, Callable
from datetime import datetime

from eventbus import DatabaseConsumer
from eventbus.schemas import VitalEvent
from database.services.uow import UnitOfWork
from database.services.deduplication import DeduplicationService
from database.models.vital import Vital
from database.metrics.prometheus import metrics

logger = structlog.get_logger(__name__)

class VitalsDatabaseConsumer:
    """
    Consumes Vital events from Redis Streams and stores them.
    Idempotent, retryable, error-handled.
    """
    
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self.consumer = DatabaseConsumer(consumer_name="db_vitals_worker")
        self.uow_factory = uow_factory
        # Bind the handler
        self.consumer.bind_handler(self.handle_event)

    async def start(self):
        """Start the consumer background task."""
        await self.consumer.start()

    async def stop(self):
        """Stop the consumer gracefully."""
        await self.consumer.stop()

    async def handle_event(self, event_dict: Dict[str, Any]) -> None:
        """
        Processes a single VitalEvent from Redis Streams.
        Called by the eventbus worker which handles retries and DLQ routing.
        """
        start_time = datetime.now()
        
        # 1. Validate payload
        try:
            event = VitalEvent(**event_dict)
        except Exception as e:
            logger.error("invalid_vital_event_schema", error=str(e), payload=event_dict)
            raise ValueError(f"Invalid schema: {e}")

        # 2. Open transaction
        async with self.uow_factory() as uow:
            
            # 3. Define the write action
            async def write_vital():
                vital = Vital(
                    client_event_id=event.event_id,
                    patient_id=event.patient_id,
                    metric=event.metric,
                    value=event.value,
                    unit=event.unit,
                    loinc=event.loinc,
                    captured_at=event.timestamp,
                    source_device=event.source_device,
                    flagged=event.flagged,
                    metadata_payload=event.metadata
                )
                await uow.vitals.create(vital.to_dict()) # Use dict for generic create, or map explicitly
                # To be precise with the repository pattern, since create takes a dict:
                # But creating via model instance and uow.add is cleaner for ORMs.
                # Let's use uow.add directly
                await uow.add(vital)
                metrics.inc_db_writes("vitals", "sqlite") # Tier 1 write

            # 4. Execute with Idempotency
            executed = await DeduplicationService.execute_idempotent(
                uow=uow,
                entity_type="vital",
                client_event_id=event.event_id,
                action=write_vital
            )

            # Note: UoW will commit automatically on exit if no exception
            if executed:
                logger.debug(
                    "vital_stored", 
                    patient=event.patient_id, 
                    metric=event.metric, 
                    val=event.value
                )

        duration = (datetime.now() - start_time).total_seconds()
        metrics.observe_storage_latency("sqlite", duration)
