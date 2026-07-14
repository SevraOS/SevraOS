"""
HELIOS OS + SEVRA AI
Device Model
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import String, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class Device(HeliosBase):
    """
    Medical devices registered in the system (e.g., bedside monitors, wearables).
    """
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique device identifier (MAC address, serial number)",
    )

    device_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="Type of device (e.g., 'patient_monitor', 'ecg_patch', 'pulse_oximeter')",
    )

    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    firmware_version: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Is the device currently allowed to connect?",
    )

    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time a heartbeat or payload was received",
    )

    assigned_patient_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Currently assigned patient ID (UUID)",
    )

    location: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Physical location if permanently mounted",
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional device-specific metadata",
    )
