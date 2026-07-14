"""
HELIOS OS + SEVRA AI
Rejected Reading Model
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class RejectedReading(HeliosBase):
    """
    Stores readings that failed Validation or Normalization.
    Keeps a record for debugging and audit without polluting the clean Vitals table.
    """
    __tablename__ = "rejected_readings"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        comment="Idempotency key from Collector",
    )

    source_device: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )

    rejection_stage: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="e.g., 'mdil_parse', 'validation_structural', 'validation_clinical', 'normalization'",
    )

    rejection_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    raw_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="The actual data that failed",
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_rejected_device_stage", "source_device", "rejection_stage"),
        Index("ix_rejected_sync_created", "sync_status", "created_at"),
    )
