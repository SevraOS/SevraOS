"""
HELIOS OS + SEVRA AI
Patient Model
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class Patient(HeliosBase):
    """
    Patient demographics and metadata.
    """
    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Medical Record Number (unique per facility)",
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    date_of_birth: Mapped[Optional[Date]] = mapped_column(
        Date,
        nullable=True,
    )

    gender: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    location: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Ward/Bed/Room location",
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Extensible patient metadata (allergies, primary care physician, etc.)",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
