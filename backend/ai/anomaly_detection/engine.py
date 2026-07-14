"""
HELIOS OS + SEVRA AI
Anomaly Detection Engine (Section 15)
"""

from typing import Dict, Any, Optional
from ai.schemas.inference import AnomalyDetection
from datetime import datetime, timezone

class AnomalyDetector:
    """Statistical detection of vital sign deviations."""
    
    # Mocked statistical bounds (mean, std_dev)
    BOUNDS = {
        "heart_rate": (75.0, 15.0),
        "systolic_bp": (120.0, 15.0),
        "spo2": (98.0, 2.0)
    }

    @staticmethod
    def detect(patient_id: str, metric: str, value: float) -> Optional[AnomalyDetection]:
        """Detect if a single reading is an anomaly based on Z-Score."""
        bounds = AnomalyDetector.BOUNDS.get(metric)
        if not bounds:
            return None
            
        mean, std_dev = bounds
        z_score = abs(value - mean) / std_dev
        
        # Flag if Z-Score > 3.0 (approx 99.7% confidence interval)
        if z_score > 3.0:
            return AnomalyDetection(
                patient_id=patient_id,
                metric=metric,
                value=value,
                expected_range=[mean - (2*std_dev), mean + (2*std_dev)],
                deviation_z_score=z_score,
                timestamp=datetime.now(timezone.utc)
            )
        return None
