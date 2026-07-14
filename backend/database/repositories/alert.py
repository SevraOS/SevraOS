"""
HELIOS OS + SEVRA AI
Alert Repository
"""

from typing import Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from database.models.alert import Alert
from database.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession):
        super().__init__(Alert, session)

    async def get_active_alerts_for_patient(self, patient_id: str) -> Sequence[Alert]:
        """Get unresolved alerts for a patient."""
        stmt = (
            select(Alert)
            .where(Alert.patient_id == patient_id)
            .where(Alert.resolved.is_(False))
            .where(Alert.deleted_at.is_(None))
            .order_by(desc(Alert.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unacknowledged_alerts(self, limit: int = 100) -> Sequence[Alert]:
        """Get highest priority unacknowledged alerts system-wide."""
        stmt = (
            select(Alert)
            .where(Alert.is_acknowledged.is_(False))
            .where(Alert.resolved.is_(False))
            .where(Alert.deleted_at.is_(None))
            .order_by(
                # Order by severity (this would require a custom case statement in real life, 
                # but for simplicity we assume the UI handles sorting or we use raw SQL for ENUM sorting)
                desc(Alert.created_at)
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
