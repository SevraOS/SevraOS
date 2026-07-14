"""
HELIOS OS + SEVRA AI
Notification Model
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class Notification(HeliosBase):
    """
    Records of outbound notifications (SMS, Push, Pager).
    """
    __tablename__ = "notifications"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        comment="Idempotency key for the notification attempt",
    )

    recipient_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        comment="User ID, phone number, or pager ID",
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="SMS, PUSH, PAGER, EMAIL",
    )

    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
        nullable=False,
        comment="pending, sent, failed, delivered, read",
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Gateway provider response, exact payload sent, etc.",
    )

    __table_args__ = (
        Index("ix_notifications_recipient_status", "recipient_id", "status"),
        Index("ix_notifications_sync_created", "sync_status", "created_at"),
    )
