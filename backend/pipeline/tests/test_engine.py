import pytest
import asyncio
from datetime import datetime, timezone
from mdil.schema import RawReading, MetricType, Unit
from pipeline.engine import PipelineEngine
from normalization.canonical import CanonicalEvent

@pytest.fixture
def raw_reading():
    return RawReading(
        device_id="SIM-ECG-001",
        device_type="ecg",
        metric=MetricType.HEART_RATE,
        value=75.0,
        unit=Unit.BPM,
        captured_at=datetime.now(timezone.utc),
        raw_payload=b"test"
    )

@pytest.mark.asyncio
async def test_pipeline_engine_integration(raw_reading):
    published_events = []
    
    async def mock_publisher(event: CanonicalEvent) -> None:
        published_events.append(event)
        
    engine = PipelineEngine(publish_callback=mock_publisher)
    await engine.start()
    
    # Submit valid reading
    await engine.forward(raw_reading)
    
    # Submit invalid reading (Null value, should be rejected by validation, never published)
    invalid_reading = RawReading(
        device_id="SIM-ECG-001",
        device_type="ecg",
        metric=MetricType.HEART_RATE,
        value=None,
        unit=Unit.BPM,
        captured_at=datetime.now(timezone.utc),
        raw_payload=b""
    )
    await engine.forward(invalid_reading)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    await engine.stop()
    
    # Assert
    assert len(published_events) == 1
    event = published_events[0]
    assert event.patient_id == "PAT-1001"
    assert event.loinc == "8867-4"
    assert event.value == 75.0
    assert event.flagged is False
