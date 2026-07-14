"""
HELIOS OS + SEVRA AI
Vital Repository (Time-Series Optimized)
"""

from datetime import datetime
from typing import Sequence, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from database.models.vital import Vital
from database.repositories.base import BaseRepository


class VitalRepository(BaseRepository[Vital]):
    def __init__(self, session: AsyncSession):
        super().__init__(Vital, session)

    async def get_patient_timeline(
        self, 
        patient_id: str, 
        start_time: datetime, 
        end_time: datetime,
        metrics: Optional[List[str]] = None,
        limit: int = 1000
    ) -> Sequence[Vital]:
        """Fetch a time-series of vitals for a patient."""
        stmt = (
            select(Vital)
            .where(Vital.patient_id == patient_id)
            .where(Vital.captured_at >= start_time)
            .where(Vital.captured_at <= end_time)
            .where(Vital.deleted_at.is_(None))
            .order_by(desc(Vital.captured_at))
        )
        
        if metrics:
            stmt = stmt.where(Vital.metric.in_(metrics))
            
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_vital(self, patient_id: str, metric: str) -> Optional[Vital]:
        """Get the most recent reading of a specific metric for a patient."""
        stmt = (
            select(Vital)
            .where(Vital.patient_id == patient_id)
            .where(Vital.metric == metric)
            .where(Vital.deleted_at.is_(None))
            .order_by(desc(Vital.captured_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
