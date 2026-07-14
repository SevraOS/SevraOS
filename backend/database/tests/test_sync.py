"""
HELIOS OS + SEVRA AI
Tests - Sync Engine
"""

import pytest
from unittest.mock import AsyncMock, patch

from database.sync.engine import SyncEngine

@pytest.mark.asyncio
async def test_sync_engine_initialization():
    from unittest.mock import MagicMock
    mock_sqlite_factory = MagicMock()
    mock_pg_factory = MagicMock()
    
    engine = SyncEngine(mock_sqlite_factory, mock_pg_factory)
    assert engine._running is False
    assert engine._task is None
    
    await engine.start()
    assert engine._running is True
    assert engine._task is not None
    
    await engine.stop()
    assert engine._running is False
