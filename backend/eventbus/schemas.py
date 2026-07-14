import uuid
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class EventType(str, Enum):
    VITAL = "vital"
    ALERT = "alert"
    PREDICTION = "prediction"
    HOSPITAL_SYNC = "hospital_sync"
    AUDIT = "audit"
    NOTIFICATION = "notification"

class BaseEvent(BaseModel):
    """Base schema for all events flowing through the Redis Event Bus."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VitalEvent(BaseEvent):
    """Event triggered by the Normalization Layer."""
    event_type: EventType = EventType.VITAL
    patient_id: str
    metric: str
    value: float
    unit: str
    loinc: str
    source_device: str
    flagged: bool = False

class AlertEvent(BaseEvent):
    """Event triggered by AI/Rules engine indicating clinical risk."""
    event_type: EventType = EventType.ALERT
    patient_id: str
    alert_code: str
    severity: str
    message: str
    source_metric: Optional[str] = None

class PredictionEvent(BaseEvent):
    """Event triggered by AI Model predictions."""
    event_type: EventType = EventType.PREDICTION
    patient_id: str
    model_version: str
    prediction_type: str
    risk_score: float
    confidence: float

class HospitalSyncEvent(BaseEvent):
    """Event triggered to sync data to EHR (FHIR/HL7)."""
    event_type: EventType = EventType.HOSPITAL_SYNC
    patient_id: str
    sync_target: str # e.g. "epic", "cerner"
    payload: Dict[str, Any] # e.g. FHIR Observation JSON

class AuditEvent(BaseEvent):
    """Event for regulatory tracking and system auditing."""
    event_type: EventType = EventType.AUDIT
    action: str
    actor: str # system, user_id
    resource_id: str
    details: str

class NotificationEvent(BaseEvent):
    """Event to trigger mobile/pager notifications."""
    event_type: EventType = EventType.NOTIFICATION
    recipient_id: str
    channel: str # SMS, Push, Pager
    title: str
    body: str
