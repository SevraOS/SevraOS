import math
from typing import Any, Tuple
from validation.result import ValidationReason

class RuleValidator:
    """
    Validates structural and type integrity of readings.
    """
    
    @staticmethod
    def validate_reading(value: Any) -> Tuple[bool, ValidationReason]:
        """
        Check for null, missing, NaN, corrupt values, or invalid types.
        """
        if value is None:
            return False, ValidationReason.NULL_VALUE
            
        if isinstance(value, str):
            if not value.strip():
                return False, ValidationReason.CORRUPT_PAYLOAD
            try:
                # Attempt to parse to float to see if it's numeric masquerading as str
                f_val = float(value)
                if math.isnan(f_val):
                    return False, ValidationReason.CORRUPT_PAYLOAD
            except ValueError:
                return False, ValidationReason.INVALID_TYPE
                
        elif isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return False, ValidationReason.CORRUPT_PAYLOAD
        else:
            return False, ValidationReason.INVALID_TYPE
            
        return True, ValidationReason.VALID
