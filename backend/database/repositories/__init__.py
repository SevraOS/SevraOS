"""
HELIOS OS + SEVRA AI
Repository Pattern

Provides abstract and concrete repositories for interacting with the database.
Handles common CRUD operations, pagination, filtering, and bulk operations.
"""

from database.repositories.base import BaseRepository
from database.repositories.patient import PatientRepository
from database.repositories.device import DeviceRepository
from database.repositories.vital import VitalRepository
from database.repositories.alert import AlertRepository
from database.repositories.prediction import PredictionRepository

__all__ = [
    "BaseRepository",
    "PatientRepository",
    "DeviceRepository",
    "VitalRepository",
    "AlertRepository",
    "PredictionRepository",
]
