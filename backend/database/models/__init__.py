"""
HELIOS OS + SEVRA AI
Database Models — SQLAlchemy 2.x Declarative Base

All models inherit from HeliosBase which provides:
  - UUID primary keys
  - Created/updated timestamps
  - Soft-delete support (deleted_at)
  - Audit fields (created_by, updated_by)
  - Sync status tracking (SQLite→PostgreSQL)
"""

from database.models.base import HeliosBase, SyncStatus
from database.models.patient import Patient
from database.models.device import Device
from database.models.vital import Vital
from database.models.alert import Alert
from database.models.prediction import Prediction
from database.models.notification import Notification
from database.models.sync_queue import HospitalSyncQueue
from database.models.rejected_reading import RejectedReading
from database.models.audit_log import AuditLog
from database.models.system_event import SystemEvent

__all__ = [
    "HeliosBase",
    "SyncStatus",
    "Patient",
    "Device",
    "Vital",
    "Alert",
    "Prediction",
    "Notification",
    "HospitalSyncQueue",
    "RejectedReading",
    "AuditLog",
    "SystemEvent",
]
