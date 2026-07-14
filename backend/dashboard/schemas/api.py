"""
HELIOS OS + SEVRA AI
Dashboard API Schemas
"""

from typing import Generic, TypeVar, List, Optional, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    size: int
    has_next: bool

# --- Patient Schemas (Section 4) ---

class PatientResponse(BaseModel):
    id: str
    mrn: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    
    model_config = {"from_attributes": True}

# --- Device Schemas (Section 5) ---

class DeviceResponse(BaseModel):
    id: str
    device_id: str
    device_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    is_active: bool
    last_seen_at: Optional[datetime] = None
    assigned_patient_id: Optional[str] = None
    location: Optional[str] = None
    
    model_config = {"from_attributes": True}

# --- Vital Schemas (Section 6) ---

class VitalResponse(BaseModel):
    id: str
    client_event_id: str
    patient_id: str
    metric: str
    value: float
    unit: str
    loinc: str
    captured_at: datetime
    source_device: str
    flagged: bool
    
    model_config = {"from_attributes": True}

# --- Alert Schemas (Section 7) ---

class AlertResponse(BaseModel):
    id: str
    client_event_id: str
    patient_id: Optional[str] = None
    alert_code: str
    severity: str
    message: str
    source_metric: Optional[str] = None
    is_acknowledged: bool
    resolved: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

# --- Prediction Schemas (Section 8) ---

class PredictionResponse(BaseModel):
    id: str
    client_event_id: str
    patient_id: str
    model_version: str
    prediction_type: str
    risk_score: float
    confidence: float
    created_at: datetime
    metadata_payload: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}

# --- Summary Schemas ---

class PatientSummaryResponse(BaseModel):
    patient: PatientResponse
    active_alerts: List[AlertResponse]
    latest_vitals: Dict[str, VitalResponse]
    latest_predictions: List[PredictionResponse]
