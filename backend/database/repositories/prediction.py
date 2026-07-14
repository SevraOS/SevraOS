"""
HELIOS OS + SEVRA AI
Prediction Repository
"""

from typing import Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.models.prediction import Prediction
from database.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    def __init__(self, session: AsyncSession):
        super().__init__(Prediction, session)

    async def get_latest_prediction(self, patient_id: str, prediction_type: str) -> Optional[Prediction]:
        """Get the most recent AI prediction of a specific type for a patient."""
        stmt = (
            select(Prediction)
            .where(Prediction.patient_id == patient_id)
            .where(Prediction.prediction_type == prediction_type)
            .where(Prediction.deleted_at.is_(None))
            .order_by(desc(Prediction.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_prediction_history(
        self, 
        patient_id: str, 
        prediction_type: str, 
        limit: int = 50
    ) -> Sequence[Prediction]:
        """Get history of predictions to show trend (e.g., Sepsis Risk over last 24h)."""
        stmt = (
            select(Prediction)
            .where(Prediction.patient_id == patient_id)
            .where(Prediction.prediction_type == prediction_type)
            .where(Prediction.deleted_at.is_(None))
            .order_by(desc(Prediction.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
