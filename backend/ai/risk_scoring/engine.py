"""
HELIOS OS + SEVRA AI
Risk Scoring Engine (Section 14)
"""

from typing import Dict, Any
from ai.schemas.inference import RiskScore
from datetime import datetime, timezone

class RiskEngine:
    """Calculates heuristic clinical priority scores (e.g., MEWS, NEWS)."""
    
    @staticmethod
    def calculate_mews(vitals_history: Dict[str, Any]) -> RiskScore:
        """Modified Early Warning Score (MEWS)."""
        # Simplified logic for demonstration
        score = 0.0
        
        hr = vitals_history.get("heart_rate")
        sys_bp = vitals_history.get("systolic_bp")
        rr = vitals_history.get("respiratory_rate")
        temp = vitals_history.get("temperature")
        
        if hr:
            if hr > 129: score += 3
            elif hr > 110: score += 2
            elif hr > 100: score += 1
            elif hr < 40: score += 2
            elif hr <= 50: score += 1
            
        if rr:
            if rr > 29: score += 3
            elif rr > 20: score += 2
            elif rr < 9: score += 2
            
        # ... logic continues ...
        
        # Normalize score to 0.0 - 1.0 (Assume max 14)
        normalized = min(score / 14.0, 1.0)
        
        return RiskScore(
            patient_id=vitals_history.get("patient_id", "unknown"),
            score_type="MEWS",
            value=normalized,
            timestamp=datetime.now(timezone.utc)
        )
