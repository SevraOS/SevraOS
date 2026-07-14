from typing import Optional
import structlog
from mdil.schema import RawReading
from validation.result import (
    ValidationResult, ValidationStatus, ValidationReason, ValidationMetadata
)
from validation.ranges import RangeValidator
from validation.rules import RuleValidator
from validation.outliers import OutlierEngine
from validation.audit import ValidationAuditService

logger = structlog.get_logger(__name__)

class ValidationEngine:
    """
    Main entry point for the Validation Layer.
    Orchestrates structural checks, physiological ranges, and statistical outliers.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.range_validator = RangeValidator(config_path)
        self.rule_validator = RuleValidator()
        self.outlier_engine = OutlierEngine()
        self.audit_service = ValidationAuditService()
        
    def validate(self, reading: RawReading) -> ValidationResult:
        """
        Validate a RawReading from the Collector.
        Returns a ValidationResult containing status (ACCEPTED/REJECTED/FLAGGED).
        """
        # Step 1: Null & Corruption Rules
        is_valid, rule_reason = self.rule_validator.validate_reading(reading.value)
        if not is_valid:
            result = self._create_result(
                reading, ValidationStatus.REJECTED, rule_reason, "error"
            )
            self.audit_service.audit(result)
            return result
            
        # If we reach here, we know the value is structuraly valid and numeric
        try:
            numeric_value = float(reading.value)
        except (ValueError, TypeError):
             result = self._create_result(
                 reading, ValidationStatus.REJECTED, ValidationReason.INVALID_TYPE, "error"
             )
             self.audit_service.audit(result)
             return result

        # Step 2: Physiological Range Checking
        in_range, range_msg = self.range_validator.is_within_range(reading.metric, numeric_value)
        if not in_range:
            result = self._create_result(
                reading, ValidationStatus.REJECTED, ValidationReason.OUT_OF_RANGE, "error",
                audit_data={"message": range_msg}
            )
            self.audit_service.audit(result)
            return result
            
        # Step 3: Statistical Outlier Detection
        # Outliers are flagged but accepted into the normalization pipeline
        is_outlier, outlier_msg = self.outlier_engine.check_outlier(
            reading.device_id, reading.metric, numeric_value
        )
        if is_outlier:
            result = self._create_result(
                reading, ValidationStatus.FLAGGED, ValidationReason.STATISTICAL_OUTLIER, "warning",
                audit_data={"message": outlier_msg}
            )
            self.audit_service.audit(result)
            return result
            
        # Passed all checks
        return self._create_result(
            reading, ValidationStatus.ACCEPTED, ValidationReason.VALID, "info"
        )
        
    def _create_result(
        self, 
        reading: RawReading, 
        status: ValidationStatus, 
        reason: ValidationReason, 
        severity: str,
        audit_data: Optional[dict] = None
    ) -> ValidationResult:
        meta = ValidationMetadata(
            device_id=reading.device_id,
            metric=reading.metric,
            reason=reason,
            severity=severity,
            audit_data=audit_data or {}
        )
        return ValidationResult(
            status=status,
            reason=reason,
            metadata=meta,
            original_reading=reading
        )
