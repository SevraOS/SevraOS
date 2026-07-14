"""
HELIOS OS + SEVRA AI
Patient Repository
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.patient import Patient
from database.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    def __init__(self, session: AsyncSession):
        super().__init__(Patient, session)

    async def get_by_mrn(self, mrn: str) -> Optional[Patient]:
        """Fetch a patient by their Medical Record Number."""
        stmt = select(Patient).where(Patient.mrn == mrn).where(Patient.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
