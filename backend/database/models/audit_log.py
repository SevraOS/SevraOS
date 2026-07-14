"""
HELIOS OS + SEVRA AI
Audit Log Model
"""

from __future__ import annotations

from sqlalchemy import String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class AuditLog(HeliosBase):
    """
    Immutable audit trail for all system actions (PHI access, authentication, configuration changes).
    Append-only. Meets compliance requirements (HIPAA).
    """
    __tablename__ = "audit_logs"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        comment="E.g., 'USER_LOGIN', 'VIEW_PATIENT', 'ACKNOWLEDGE_ALERT'",
    )

    actor: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        comment="User ID, Service Account, or System",
    )

    resource_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        comment="The ID of the record that was accessed/modified",
    )

    details: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human readable summary",
    )

    context_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Full context (IP address, user agent, previous state vs new state)",
    )

    __table_args__ = (
        Index("ix_audit_actor_action", "actor", "action", "created_at"),
        Index("ix_audit_resource", "resource_id", "created_at"),
        Index("ix_audit_sync_created", "sync_status", "created_at"),
    )
