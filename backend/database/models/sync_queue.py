"""
HELIOS OS + SEVRA AI
Hospital Sync Queue Model
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, JSON, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class HospitalSyncQueue(HeliosBase):
    """
    Queue for sending data Outbound to the Hospital EHR (HL7/FHIR).
    Managed by the Hospital Integration Layer.
    """
    __tablename__ = "hospital_sync_queue"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        comment="Idempotency key. Usually maps to the triggering Vital or Alert event_id.",
    )

    patient_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )

    sync_target: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="E.g., 'epic_fhir', 'cerner_mllp'",
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="The transformed data ready to be sent (e.g., FHIR JSON or HL7v2 base64)",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
        nullable=False,
        comment="pending, processing, success, failed, dead_letter",
    )

    send_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_hospital_sync_target_status", "sync_target", "status", "created_at"),
        Index("ix_hospital_sync_sync_created", "sync_status", "created_at"),
    )
