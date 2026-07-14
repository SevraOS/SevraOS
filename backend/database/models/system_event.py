"""
HELIOS OS + SEVRA AI
System Event Model
"""

from __future__ import annotations

from sqlalchemy import String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class SystemEvent(HeliosBase):
    """
    Events related to the HELIOS OS itself (service starts, crashes, sync failures, configuration updates).
    """
    __tablename__ = "system_events"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    component: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="E.g., 'mdil', 'database_service', 'sync_engine'",
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="E.g., 'STARTUP', 'SHUTDOWN', 'SYNC_ERROR', 'HEARTBEAT_LOST'",
    )

    severity: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        comment="INFO, WARN, ERROR, CRITICAL",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    metadata_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Stack traces, configuration values, host metrics",
    )

    __table_args__ = (
        Index("ix_system_component_type", "component", "event_type", "created_at"),
        Index("ix_system_sync_created", "sync_status", "created_at"),
    )
