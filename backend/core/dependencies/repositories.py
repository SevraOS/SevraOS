"""
HELIOS OS + SEVRA AI
Base Repository Pattern

Generic async repository base class.
All service repositories inherit from BaseRepository.
Provides standard CRUD operations with SQLAlchemy 2.x async sessions.
Future modules define their domain repositories by extending this base.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository.
    Provides CRUD primitives for SQLAlchemy declarative models.

    Usage:
        class PatientRepository(BaseRepository[Patient]):
            model = Patient

        repo = PatientRepository(session)
        patient = await repo.get_by_id("uuid-string")
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: str | UUID) -> ModelT | None:
        """Fetch a single record by primary key (id field)."""
        result = await self._session.get(self.model, str(entity_id))
        return result

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelT]:
        """Fetch a paginated list of records with optional filters."""
        stmt = select(self.model)
        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    stmt = stmt.where(column == value)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total records with optional filters."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    stmt = stmt.where(column == value)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, entity: ModelT) -> ModelT:
        """Persist a new entity and return it with DB-generated fields populated."""
        self._session.add(entity)
        await self._session.flush()  # Gets auto-generated IDs without committing
        await self._session.refresh(entity)
        logger.debug(
            "repository_create",
            model=self.model.__name__,
        )
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """Merge and persist changes to an existing entity."""
        merged = await self._session.merge(entity)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_by_id(self, entity_id: str | UUID) -> bool:
        """
        Soft-delete by ID (sets deleted_at if the model supports it).
        Falls back to hard-delete if the model has no deleted_at column.
        Returns True if an entity was deleted, False if not found.
        """
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return False

        if hasattr(entity, "deleted_at"):
            from datetime import datetime, timezone
            setattr(entity, "deleted_at", datetime.now(timezone.utc))
            await self._session.flush()
        else:
            await self._session.delete(entity)
            await self._session.flush()

        logger.debug(
            "repository_delete",
            model=self.model.__name__,
            entity_id=str(entity_id),
        )
        return True

    async def exists(self, entity_id: str | UUID) -> bool:
        """Check if an entity exists by ID."""
        entity = await self.get_by_id(entity_id)
        return entity is not None


class RepositoryRegistry:
    """
    Central registry for all domain repositories.
    Future modules register their repositories here.
    Injected via ServiceContainer.

    Usage in endpoints:
        repos = Depends(get_repositories)
        patient = await repos.patients.get_by_id(patient_id)
    """

    def __init__(self, sqlite_session: AsyncSession, postgres_session: AsyncSession | None = None) -> None:
        self._sqlite = sqlite_session
        self._postgres = postgres_session

        # ── Foundation repositories ────────────────────────────────────────
        # (None at foundation level — added per service module)

        # ── Future module repository slots ─────────────────────────────────
        # self.patients = PatientRepository(sqlite_session)      # Added in Database module
        # self.devices = DeviceRepository(sqlite_session)        # Added in MDIL module
        # self.users = UserRepository(postgres_session)          # Added in Security module
        # self.audit_logs = AuditLogRepository(postgres_session) # Added in Security module
