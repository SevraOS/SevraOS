"""
HELIOS OS + SEVRA AI
Tests - Failure Recovery Orchestrator
"""

import pytest
from unittest.mock import AsyncMock

from database.services.recovery import Orchestrator

@pytest.mark.asyncio
async def test_orchestrator_starts_offline_if_pg_down():
    mock_health = AsyncMock()
    mock_health.check_postgresql.return_value = False # PG is down
    mock_sync = AsyncMock()
    mock_consumer = AsyncMock()
    
    orchestrator = Orchestrator(mock_health, mock_sync, [mock_consumer])
    
    # Test boot process
    await orchestrator.start()
    
    assert orchestrator._is_offline_mode is True
    # Sync engine should NOT be started if PG is down
    mock_sync.start.assert_not_called()
    # But consumers SHOULD start (Offline-first)
    mock_consumer.start.assert_called_once()

    await orchestrator.stop()
