"""
HELIOS OS + SEVRA AI
Idempotent Storage - SECTION 8
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.vital import Vital
from database.models.alert import Alert
from database.models.prediction import Prediction
from database.services.uow import UnitOfWork

logger = structlog.get_logger(__name__)

class DeduplicationService:
    """
    Ensures exactly-once storage semantics by checking client_event_id.
    Works for SQLite and PostgreSQL.
    """
    
    @staticmethod
    async def is_duplicate_vital(uow: UnitOfWork, client_event_id: str) -> bool:
        """Check if a vital with this ID already exists."""
        stmt = select(Vital.id).where(Vital.client_event_id == client_event_id)
        result = await uow.session.execute(stmt)
        return result.first() is not None

    @staticmethod
    async def is_duplicate_alert(uow: UnitOfWork, client_event_id: str) -> bool:
        """Check if an alert with this ID already exists."""
        stmt = select(Alert.id).where(Alert.client_event_id == client_event_id)
        result = await uow.session.execute(stmt)
        return result.first() is not None

    @staticmethod
    async def is_duplicate_prediction(uow: UnitOfWork, client_event_id: str) -> bool:
        """Check if a prediction with this ID already exists."""
        stmt = select(Prediction.id).where(Prediction.client_event_id == client_event_id)
        result = await uow.session.execute(stmt)
        return result.first() is not None

    @staticmethod
    async def execute_idempotent(uow: UnitOfWork, entity_type: str, client_event_id: str, action: callable) -> bool:
        """
        Generic execution wrapper for idempotent writes.
        Returns True if action was executed, False if it was a duplicate.
        """
        is_dup = False
        if entity_type == "vital":
            is_dup = await DeduplicationService.is_duplicate_vital(uow, client_event_id)
        elif entity_type == "alert":
            is_dup = await DeduplicationService.is_duplicate_alert(uow, client_event_id)
        elif entity_type == "prediction":
            is_dup = await DeduplicationService.is_duplicate_prediction(uow, client_event_id)
        else:
            raise ValueError(f"Unknown entity type for deduplication: {entity_type}")

        if is_dup:
            logger.debug(
                "idempotent_write_skipped", 
                entity_type=entity_type, 
                client_event_id=client_event_id
            )
            return False

        await action()
        return True
