"""
HELIOS OS + SEVRA AI
AI Engine Tests (Section 23)
"""

import pytest
from datetime import datetime, timezone
from ai.anomaly_detection.engine import AnomalyDetector
from ai.risk_scoring.engine import RiskEngine
from ai.prediction_engine.aggregator import PredictionAggregator
from ai.alert_engine.generator import AlertEngine

def test_anomaly_detection():
    # Heart rate bounds are (75.0, 15.0). 
    # Z-score > 3 means outside 75 +/- 45 -> < 30 or > 120
    
    # Normal
    normal = AnomalyDetector.detect("p1", "heart_rate", 80.0)
    assert normal is None
    
    # Anomaly High
    anomaly = AnomalyDetector.detect("p1", "heart_rate", 130.0)
    assert anomaly is not None
    assert anomaly.deviation_z_score > 3.0
    
def test_risk_engine_mews():
    # Normal
    normal_risk = RiskEngine.calculate_mews({
        "heart_rate": 70,
        "respiratory_rate": 15
    })
    assert normal_risk.value == 0.0
    
    # Critical
    critical_risk = RiskEngine.calculate_mews({
        "heart_rate": 135, # +3
        "respiratory_rate": 35 # +3
    })
    assert critical_risk.value > 0.0

def test_alert_engine():
    # Setup mock prediction
    from ai.schemas.inference import PredictionEvent
    
    # Low Risk
    low_pred = PredictionEvent(
        event_id="e1", patient_id="p1", prediction_type="type",
        risk_score=0.1, confidence=0.9, timestamp=datetime.now(timezone.utc),
        metadata={}
    )
    assert AlertEngine.evaluate(low_pred) is None
    
    # Critical Risk
    crit_pred = PredictionEvent(
        event_id="e1", patient_id="p1", prediction_type="type",
        risk_score=0.9, confidence=0.9, timestamp=datetime.now(timezone.utc),
        metadata={}
    )
    alert = AlertEngine.evaluate(crit_pred)
    assert alert is not None
    assert alert.severity == "CRITICAL"
