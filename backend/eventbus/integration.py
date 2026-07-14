"""
HELIOS OS + SEVRA AI — Pipeline Integration Bridge
Section 19: Normalization → Event Bus

This module provides the concrete wiring between the PipelineEngine
(Normalization output) and the Redis Event Bus (EventProducer).

Architecture:
    Collector
      └─► PipelineEngine.forward()
            └─► ValidationEngine
                  └─► NormalizerEngine
                        └─► EventBusBridge.publish()
                              └─► EventProducer → Redis Stream

Integration interfaces for downstream services (Sections 6-8):
    - DatabaseServiceInterface    (stub — implemented in Prompt 6)
    - AIServiceInterface          (stub — implemented in Prompt 7)
    - NotificationServiceInterface (stub — implemented in Prompt 8)
    - HospitalSyncInterface       (stub — implemented in Prompt 9)
"""
from __future__ import annotations

import abc
import time
import structlog
from typing import Optional, Dict, Any

from normalization.canonical import CanonicalEvent
from eventbus.producer import EventProducer
from eventbus.streams import StreamTopic
from eventbus.schemas import VitalEvent, EventType
from eventbus.metrics import metrics

logger = structlog.get_logger(__name__)


# ── Downstream Service Interfaces (contracts only) ─────────────────────────────

class DatabaseServiceInterface(abc.ABC):
    """
    Contract for the Database Consumer Service (Prompt 6).
    Receives CanonicalEvents for persistent storage.
    """

    @abc.abstractmethod
    async def store_vital(self, event: CanonicalEvent) -> None: ...


class AIServiceInterface(abc.ABC):
    """
    Contract for the AI Inference Service (Prompt 7).
    Receives CanonicalEvents for real-time risk scoring.
    """

    @abc.abstractmethod
    async def score(self, event: CanonicalEvent) -> Optional[Dict[str, Any]]: ...


class NotificationServiceInterface(abc.ABC):
    """
    Contract for the Notification Service (Prompt 8).
    Receives AlertEvents and dispatches to mobile/pager channels.
    """

    @abc.abstractmethod
    async def dispatch(self, event_dict: Dict[str, Any]) -> None: ...


class HospitalSyncInterface(abc.ABC):
    """
    Contract for the Hospital EHR Sync Service (Prompt 9).
    Receives CanonicalEvents and translates to FHIR/HL7 for external systems.
    """

    @abc.abstractmethod
    async def sync(self, event: CanonicalEvent) -> None: ...


# ── Event Bus Bridge ───────────────────────────────────────────────────────────

class EventBusBridge:
    """
    Concrete publish callback used by PipelineEngine.

    Transforms a CanonicalEvent (Normalization output) into a VitalEvent
    (Event Bus schema) and publishes it to the Redis VITALS stream.

    This is the only place in the system that crosses the boundary
    between the Normalization layer and the Event Bus.
    """

    def __init__(self) -> None:
        self._producer = EventProducer()

    async def publish(self, event: CanonicalEvent) -> None:
        """
        Called by PipelineEngine._process_reading() after normalization.
        Converts CanonicalEvent → VitalEvent → Redis Stream.
        """
        t_start = time.perf_counter()

        vital = VitalEvent(
            patient_id=event.patient_id,
            metric=event.metric,
            value=event.value,
            unit=event.unit,
            loinc=event.loinc,
            source_device=event.source_device,
            flagged=event.flagged,
        )

        msg_id = await self._producer.publish(StreamTopic.VITALS.value, vital)

        elapsed = time.perf_counter() - t_start
        metrics.observe_processing("pipeline_bridge", elapsed)

        if msg_id:
            logger.debug(
                "vital_published_to_event_bus",
                patient_id=event.patient_id,
                metric=event.metric,
                stream=StreamTopic.VITALS.value,
                msg_id=msg_id,
            )
        else:
            logger.warning(
                "vital_buffered_offline",
                patient_id=event.patient_id,
                metric=event.metric,
            )


def build_pipeline_engine() -> "PipelineEngine":  # type: ignore[name-defined]  # noqa: F821
    """
    Factory: creates a PipelineEngine pre-wired to publish to the Redis Event Bus.

    Usage (in startup.py):
        from eventbus.integration import build_pipeline_engine
        engine = build_pipeline_engine()
        await engine.start()
    """
    from pipeline.engine import PipelineEngine

    bridge = EventBusBridge()
    return PipelineEngine(publish_callback=bridge.publish)
