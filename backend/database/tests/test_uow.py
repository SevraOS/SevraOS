"""
HELIOS OS + SEVRA AI
Tests - Unit of Work
"""

import pytest
from unittest.mock import AsyncMock

from database.services.uow import UnitOfWork
from database.models.vital import Vital

@pytest.mark.asyncio
async def test_uow_commit_on_success():
    mock_session = AsyncMock()
    mock_session_factory = lambda: mock_session
    
    uow = UnitOfWork(mock_session_factory)
    
    async with uow:
        # Do some work
        vital = Vital(client_event_id="123", patient_id="456", metric="hr", value=80, unit="bpm", loinc="1", source_device="A")
        await uow.add(vital)
        
    # Exited context without error, should have committed
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once()
    mock_session.add.assert_called_once_with(vital)

@pytest.mark.asyncio
async def test_uow_rollback_on_error():
    mock_session = AsyncMock()
    mock_session_factory = lambda: mock_session
    
    uow = UnitOfWork(mock_session_factory)
    
    with pytest.raises(ValueError):
        async with uow:
            raise ValueError("Something went wrong")
            
    # Exited context WITH error, should have rolled back
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()
