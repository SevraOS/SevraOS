import structlog
from typing import Any
from datetime import datetime, timezone
from validation.result import ValidationResult, ValidationStatus

logger = structlog.get_logger(__name__)

class ValidationAuditService:
    """
    Records and audits rejected or flagged readings.
    In a production system, this could write to a persistent audit database table,
    or a dedicated audit log file / stream.
    """
    
    def __init__(self):
        # We can hold a reference to an external logging/DB service here
        pass

    def audit(self, result: ValidationResult) -> None:
        """Log rejected or flagged readings for compliance and auditing."""
        if result.status == ValidationStatus.ACCEPTED:
            return
            
        log_payload = {
            "device_id": result.metadata.device_id,
            "metric": result.metadata.metric,
            "status": result.status.value,
            "reason": result.reason.value,
            "severity": result.metadata.severity,
            "timestamp": result.metadata.timestamp.isoformat(),
            "audit_data": result.metadata.audit_data,
            # We must carefully stringify original_reading as it could be complex
            "original_payload": str(result.original_reading)
        }
        
        if result.status == ValidationStatus.REJECTED:
            logger.warning("validation_rejected", **log_payload)
        elif result.status == ValidationStatus.FLAGGED:
            logger.info("validation_flagged", **log_payload)
