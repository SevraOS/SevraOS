"""
HELIOS OS + SEVRA AI
Vital Model (Clinical Observations) - SECTION 4 VITALS TABLE DESIGN
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Boolean, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class Vital(HeliosBase):
    """
    Clinical observation (Vital Sign).
    Optimized for time-series queries and sync idempotency.
    """
    __tablename__ = "vitals"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        comment="Original UUID assigned by Collector. The idempotency key.",
    )

    patient_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
        comment="Reference to Patient.id",
    )

    metric: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="Standardized metric name (e.g., 'heart_rate', 'spo2')",
    )

    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Numerical value of the observation",
    )

    unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="UCUM standard unit",
    )

    loinc: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        comment="LOINC code for interoperability",
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Time the reading was actually captured by the device (UTC)",
    )

    source_device: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        comment="Device ID that generated this vital",
    )

    flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Flagged by validation as unusual/outlier",
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Extra info: signal quality, battery level, etc.",
    )

    # ── Composite Indexes for Time-Series Optimization ───────────────────────
    # NOTE: sync_status and created_at are inherited from HeliosBase and already
    # have individual indexes there. A composite index referencing inherited columns
    # by string raises InvalidRequestError on SQLAlchemy 2.0+ with abstract bases.
    __table_args__ = (
        Index("ix_vitals_patient_metric_captured", "patient_id", "metric", "captured_at"),
        Index("ix_vitals_patient_captured", "patient_id", "captured_at"),
    )
