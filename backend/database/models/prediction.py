"""
HELIOS OS + SEVRA AI
Prediction Model
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import HeliosBase


class Prediction(HeliosBase):
    """
    AI Model Inference Results (e.g., Sepsis Risk, Deterioration Index).
    """
    __tablename__ = "predictions"

    client_event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        comment="Idempotency key from AI Engine",
    )

    patient_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Identifier for the exact AI model version used",
    )

    prediction_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        comment="Type of prediction (e.g., 'sepsis_risk_6h', 'mortality_risk')",
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Normalized score, usually 0.0 to 1.0 or 0 to 100",
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model confidence in the prediction (0.0 to 1.0)",
    )

    metadata_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Feature importance, contributing factors, SHAP values",
    )

    __table_args__ = (
        Index("ix_predictions_patient_type", "patient_id", "prediction_type", "created_at"),
        Index("ix_predictions_sync_created", "sync_status", "created_at"),
    )
