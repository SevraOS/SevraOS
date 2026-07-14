"""
HELIOS OS + SEVRA AI
AI Engine Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class InferenceRequest(BaseModel):
    """Payload sent to ONNX model."""
    patient_id: str
    features: List[float] = Field(..., description="Normalized feature vector")
    timestamp: datetime

class InferenceResult(BaseModel):
    """Raw output from ONNX model."""
    model_id: str
    version: str
    prediction: float
    confidence: float
    inference_time_ms: float

class RiskScore(BaseModel):
    """Calculated clinical risk."""
    patient_id: str
    score_type: str = Field(..., description="MEWS, NEWS, SEPSIS")
    value: float
    timestamp: datetime

class AnomalyDetection(BaseModel):
    """Statistical anomaly found in time-series."""
    patient_id: str
    metric: str
    value: float
    expected_range: List[float]
    deviation_z_score: float
    timestamp: datetime

class PredictionEvent(BaseModel):
    """Final unified prediction published to DB and WS."""
    event_id: str
    patient_id: str
    prediction_type: str
    risk_score: float
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any]

class AlertRecommendation(BaseModel):
    """Alert triggered by AI."""
    event_id: str
    patient_id: str
    alert_code: str
    severity: str
    message: str
    source_metric: Optional[str]
    timestamp: datetime
