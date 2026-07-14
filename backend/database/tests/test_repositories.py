"""
HELIOS OS + SEVRA AI
Tests - Repositories
"""

import pytest
from unittest.mock import AsyncMock

from database.models.patient import Patient
from database.repositories.patient import PatientRepository

@pytest.mark.asyncio
async def test_patient_repository_get_by_mrn():
    mock_session = AsyncMock()
    
    # Setup mock result
    mock_patient = Patient(id="123", mrn="MRN-123", first_name="John")
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_patient
    mock_session.execute.return_value = mock_result
    
    repo = PatientRepository(mock_session)
    result = await repo.get_by_mrn("MRN-123")
    
    assert result is not None
    assert result.mrn == "MRN-123"
    assert result.first_name == "John"
    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_base_repository_create():
    mock_session = AsyncMock()
    repo = PatientRepository(mock_session)
    
    obj_in = {"mrn": "MRN-456", "first_name": "Jane"}
    result = await repo.create(obj_in)
    
    assert result.mrn == "MRN-456"
    mock_session.add.assert_called_once_with(result)

@pytest.mark.asyncio
async def test_base_repository_soft_delete():
    mock_session = AsyncMock()
    repo = PatientRepository(mock_session)
    
    # Mock getting the object first
    mock_patient = Patient(id="123", mrn="MRN-123")
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_patient
    mock_session.execute.return_value = mock_result
    
    success = await repo.soft_delete("123", actor="admin")
    
    assert success is True
    assert mock_patient.is_deleted is True
    assert mock_patient.updated_by == "admin"
    assert mock_patient.sync_status == "pending" # Must trigger sync on delete
    mock_session.add.assert_called_once_with(mock_patient)
