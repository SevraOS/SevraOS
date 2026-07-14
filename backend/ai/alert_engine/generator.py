"""
HELIOS OS + SEVRA AI
Alert Generation Engine (Section 18)
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
import structlog

from ai.schemas.inference import PredictionEvent, AlertRecommendation
from ai.config import ai_config

logger = structlog.get_logger(__name__)

class AlertEngine:
    """Evaluates unified predictions to generate actionable alerts."""
    
    @staticmethod
    def evaluate(prediction: PredictionEvent) -> Optional[AlertRecommendation]:
        severity = None
        alert_code = "UNKNOWN"
        message = ""
        
        if prediction.risk_score >= ai_config.CRITICAL_RISK_THRESHOLD:
            severity = "CRITICAL"
            alert_code = "DETERIORATION_CRITICAL"
            message = f"Immediate attention required. High deterioration risk ({prediction.risk_score:.2f})."
        elif prediction.risk_score >= ai_config.HIGH_RISK_THRESHOLD:
            severity = "HIGH"
            alert_code = "DETERIORATION_WARNING"
            message = f"Patient showing signs of clinical deterioration ({prediction.risk_score:.2f})."
            
        if not severity:
            return None
            
        alert = AlertRecommendation(
            event_id=str(uuid.uuid4()),
            patient_id=prediction.patient_id,
            alert_code=alert_code,
            severity=severity,
            message=message,
            source_metric=prediction.metadata.get("anomaly_detected"),
            timestamp=datetime.now(timezone.utc)
        )
        
        logger.warning("alert_generated", patient=prediction.patient_id, severity=severity)
        return alert
