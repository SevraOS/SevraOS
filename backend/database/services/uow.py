"""
HELIOS OS + SEVRA AI
Unit Of Work Pattern - SECTION 6
"""

import structlog
from typing import Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.repositories.patient import PatientRepository
from database.repositories.device import DeviceRepository
from database.repositories.vital import VitalRepository
from database.repositories.alert import AlertRepository
from database.repositories.prediction import PredictionRepository
from database.models.base import HeliosBase

logger = structlog.get_logger(__name__)

class UnitOfWork:
    """
    Unit of Work pattern.
    Ensures all database operations within a context manager block are part of 
    a single transaction. Supports rollback on error and graceful commit.
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self.session: AsyncSession = None  # type: ignore

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self.patients = PatientRepository(self.session)
        self.devices = DeviceRepository(self.session)
        self.vitals = VitalRepository(self.session)
        self.alerts = AlertRepository(self.session)
        self.predictions = PredictionRepository(self.session)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
            logger.error(
                "transaction_rollback", 
                exc_type=str(exc_type), 
                error=str(exc_val)
            )
        else:
            await self.commit()
            
        await self.session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        try:
            await self.session.commit()
        except Exception as e:
            logger.error("commit_failed", error=str(e))
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

    async def add(self, entity: HeliosBase) -> None:
        """Generic add."""
        self.session.add(entity)
