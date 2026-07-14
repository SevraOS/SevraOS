"""Tests for the Pipeline → Event Bus integration bridge."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from normalization.canonical import CanonicalEvent
from datetime import datetime, timezone


@pytest.fixture
def canonical_event():
    return CanonicalEvent(
        patient_id="PAT-1234",
        source_device="SIM-001",
        metric="heart_rate",
        value=78.0,
        unit="bpm",
        loinc="8867-4",
        captured_at=datetime.now(timezone.utc),
        flagged=False,
    )


@pytest.mark.asyncio
async def test_bridge_publishes_vital_event(canonical_event, fake_redis):
    """EventBusBridge must publish a VitalEvent to the VITALS stream."""
    from eventbus.integration import EventBusBridge
    from eventbus.streams import StreamTopic
    from eventbus.serializer import EventSerializer

    bridge = EventBusBridge()
    await bridge.publish(canonical_event)

    msgs = await fake_redis.xrange(StreamTopic.VITALS.value, min="-", max="+")
    assert len(msgs) == 1

    data = EventSerializer.from_bytes(msgs[0][1][b"payload"])
    assert data["patient_id"] == "PAT-1234"
    assert data["metric"] == "heart_rate"
    assert data["value"] == 78.0
    assert data["flagged"] is False


@pytest.mark.asyncio
async def test_bridge_sets_flagged_true(fake_redis):
    """Flagged CanonicalEvents must propagate the flagged=True field."""
    from eventbus.integration import EventBusBridge
    from eventbus.streams import StreamTopic
    from eventbus.serializer import EventSerializer

    event = CanonicalEvent(
        patient_id="PAT-5555",
        source_device="SIM-002",
        metric="heart_rate",
        value=220.0,
        unit="bpm",
        loinc="8867-4",
        captured_at=datetime.now(timezone.utc),
        flagged=True,
    )

    bridge = EventBusBridge()
    await bridge.publish(event)

    msgs = await fake_redis.xrange(StreamTopic.VITALS.value, min="-", max="+")
    data = EventSerializer.from_bytes(msgs[0][1][b"payload"])
    assert data["flagged"] is True


def test_build_pipeline_engine_wires_bridge():
    """build_pipeline_engine() must return a PipelineEngine with a callback."""
    from eventbus.integration import build_pipeline_engine
    from pipeline.engine import PipelineEngine

    engine = build_pipeline_engine()
    assert isinstance(engine, PipelineEngine)
    assert callable(engine.publish_callback)


@pytest.mark.asyncio
async def test_downstream_interfaces_are_abstract():
    """Downstream interface stubs must be abstract (not directly instantiable)."""
    import inspect
    from eventbus.integration import (
        DatabaseServiceInterface,
        AIServiceInterface,
        NotificationServiceInterface,
        HospitalSyncInterface,
    )

    for iface in [DatabaseServiceInterface, AIServiceInterface,
                  NotificationServiceInterface, HospitalSyncInterface]:
        assert inspect.isabstract(iface), f"{iface.__name__} should be abstract"
