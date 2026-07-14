from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FLAGGED = "flagged"

class ValidationReason(str, Enum):
    VALID = "valid"
    NULL_VALUE = "null_value"
    OUT_OF_RANGE = "out_of_range"
    STATISTICAL_OUTLIER = "statistical_outlier"
    INVALID_TYPE = "invalid_type"
    CORRUPT_PAYLOAD = "corrupt_payload"
    MISSING_FIELD = "missing_field"

@dataclass
class ValidationMetadata:
    device_id: str
    metric: str
    reason: ValidationReason
    severity: str = "info"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    audit_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    status: ValidationStatus
    reason: ValidationReason
    metadata: ValidationMetadata
    original_reading: Any  # The RawReading object
