from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

@dataclass
class CanonicalEvent:
    """
    The universal data structure for normalized clinical readings.
    This is what gets pushed to the Redis Event Bus.
    """
    patient_id: str
    metric: str           # Original metric name from device
    value: float          # Converted to standard unit
    unit: str             # Standard UCUM unit
    loinc: str            # Mapped LOINC code
    captured_at: datetime # Always UTC
    source_device: str    # device_id
    flagged: bool         # True if Validation layer flagged it (e.g. Statistical Outlier)
    client_event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "loinc": self.loinc,
            "captured_at": self.captured_at.isoformat(),
            "source_device": self.source_device,
            "flagged": self.flagged,
            "client_event_id": self.client_event_id,
            "metadata": self.metadata
        }
