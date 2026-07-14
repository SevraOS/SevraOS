"""
HELIOS OS + SEVRA AI
Tests - Vitals Consumer
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from eventbus.schemas import VitalEvent, EventType
from database.consumers.vitals_consumer import VitalsDatabaseConsumer
from database.models.vital import Vital

@pytest.mark.asyncio
async def test_vitals_consumer_handle_event():
    # Mock the Unit of Work and Repositories
    mock_uow = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None
    mock_vitals_repo = AsyncMock()
    mock_uow.vitals = mock_vitals_repo
    
    def uow_factory():
        return mock_uow

    # Create the consumer
    consumer = VitalsDatabaseConsumer(uow_factory=uow_factory)

    # Construct a valid event
    event_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    
    event_payload = {
        "event_id": event_id,
        "event_type": "vital",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patient_id": patient_id,
        "metric": "heart_rate",
        "value": 85.0,
        "unit": "bpm",
        "loinc": "8867-4",
        "source_device": "device-123",
        "flagged": False,
        "metadata": {"signal_quality": "good"}
    }

    # Mock DeduplicationService to return False (not a duplicate)
    with patch('database.consumers.vitals_consumer.DeduplicationService.execute_idempotent') as mock_dedup:
        # Simulate execute_idempotent behavior: call the action and return True
        async def fake_execute(uow, entity_type, client_event_id, action):
            await action()
            return True
            
        mock_dedup.side_effect = fake_execute

        # Execute
        await consumer.handle_event(event_payload)

        # Assertions
        mock_dedup.assert_called_once()
        # Verify the UoW add was called with the Vital instance
        mock_uow.add.assert_called_once()
        added_model = mock_uow.add.call_args[0][0]
        
        assert isinstance(added_model, Vital)
        assert added_model.client_event_id == event_id
        assert added_model.metric == "heart_rate"
        assert added_model.value == 85.0

@pytest.mark.asyncio
async def test_vitals_consumer_invalid_schema():
    mock_uow = AsyncMock()
    consumer = VitalsDatabaseConsumer(uow_factory=lambda: mock_uow)

    # Missing required fields
    invalid_payload = {
        "event_type": "vital",
        "metric": "heart_rate"
    }

    with pytest.raises(ValueError) as excinfo:
        await consumer.handle_event(invalid_payload)
        
    assert "Invalid schema" in str(excinfo.value)
    mock_uow.add.assert_not_called()
