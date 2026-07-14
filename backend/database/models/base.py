"""
HELIOS OS + SEVRA AI
Database Models — Base Model

Provides the declarative base and common mixins that every model inherits.
Follows healthcare data patterns:
  - UUID primary keys (globally unique across facilities)
  - Immutable created_at timestamps
  - Soft-delete (deleted_at) — records are NEVER physically deleted within retention window
  - Audit fields for PHI access tracking
  - Sync status for offline-first SQLite→PostgreSQL replication
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class SyncStatus(str, enum.Enum):
    """Sync state for SQLite→PostgreSQL replication."""
    PENDING = "pending"
    SYNCED = "synced"
    ERROR = "error"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class HeliosBase(DeclarativeBase):
    """
    Abstract declarative base for all HELIOS database models.

    Every table gets:
      id            — UUID v4 primary key (string for SQLite compatibility)
      created_at    — Immutable UTC timestamp
      updated_at    — Auto-updated UTC timestamp
      deleted_at    — Soft-delete timestamp (NULL = active)
      created_by    — Actor who created the record (system, user_id, device_id)
      updated_by    — Actor who last modified the record
      sync_status   — Replication state for SQLite→PostgreSQL
      sync_attempts — Number of sync attempts
      last_sync_at  — Last sync attempt timestamp
      sync_error    — Last sync error message
    """
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_generate_uuid,
        comment="UUID v4 primary key",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        index=True,
        comment="Immutable creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
        comment="Last update timestamp (UTC)",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
        comment="Soft-delete timestamp (NULL = active record)",
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        default="system",
        nullable=False,
        comment="Actor who created this record",
    )

    updated_by: Mapped[str] = mapped_column(
        String(128),
        default="system",
        nullable=False,
        comment="Actor who last modified this record",
    )

    # ── Sync Status (SQLite → PostgreSQL) ────────────────────────────────────
    sync_status: Mapped[str] = mapped_column(
        String(16),
        default=SyncStatus.PENDING.value,
        nullable=False,
        index=True,
        comment="Replication state: pending | synced | error",
    )

    sync_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of sync attempts",
    )

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        comment="Last sync attempt timestamp",
    )

    sync_error: Mapped[Optional[str]] = mapped_column(
        Text,
        default=None,
        nullable=True,
        comment="Last sync error message",
    )

    def soft_delete(self, actor: str = "system") -> None:
        """Mark this record as soft-deleted."""
        self.deleted_at = _utcnow()
        self.updated_by = actor
        self.sync_status = SyncStatus.PENDING.value

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_synced(self) -> bool:
        return self.sync_status == SyncStatus.SYNCED.value

    def mark_synced(self) -> None:
        """Mark record as successfully synced to PostgreSQL."""
        self.sync_status = SyncStatus.SYNCED.value
        self.last_sync_at = _utcnow()
        self.sync_error = None

    def mark_sync_error(self, error: str) -> None:
        """Mark record as having a sync error."""
        self.sync_status = SyncStatus.ERROR.value
        self.sync_attempts += 1
        self.last_sync_at = _utcnow()
        self.sync_error = error

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, enum.Enum):
                value = value.value
            result[column.name] = value
        return result
