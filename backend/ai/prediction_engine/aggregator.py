"""
HELIOS OS + SEVRA AI
Prediction Aggregator (Section 16)
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
import structlog

from ai.schemas.inference import PredictionEvent, RiskScore, AnomalyDetection

logger = structlog.get_logger(__name__)

class PredictionAggregator:
    """
    Aggregates ONNX inference, Risk Scores, and Anomalies into a unified Prediction.
    """
    
    @staticmethod
    def aggregate(
        patient_id: str,
        inference_result: Optional[dict] = None,
        risk_score: Optional[RiskScore] = None,
        anomaly: Optional[AnomalyDetection] = None
    ) -> PredictionEvent:
        
        # Weighted synthesis of factors (Mocked logic)
        final_risk = 0.0
        confidence = 0.8
        metadata = {}
        
        if inference_result:
            final_risk += inference_result["prediction"] * 0.6
            metadata["model_prediction"] = inference_result["prediction"]
            
        if risk_score:
            final_risk += risk_score.value * 0.3
            metadata["mews_score"] = risk_score.value
            
        if anomaly:
            final_risk += 0.1 # Flat bump for active anomaly
            metadata["anomaly_detected"] = anomaly.metric
            
        final_risk = min(final_risk, 1.0)
        
        event = PredictionEvent(
            event_id=str(uuid.uuid4()),
            patient_id=patient_id,
            prediction_type="clinical_deterioration",
            risk_score=final_risk,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
        
        logger.info("prediction_aggregated", patient_id=patient_id, risk_score=final_risk)
        return event
