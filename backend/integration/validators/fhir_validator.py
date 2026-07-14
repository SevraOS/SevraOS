"""
HELIOS OS + SEVRA AI
FHIR Validation (Section 3)
"""

from pydantic import ValidationError
import structlog
from integration.fhir.models import Observation

logger = structlog.get_logger(__name__)

class FHIRValidator:
    """Validates outgoing FHIR R4 payloads against strict schemas."""
    
    @staticmethod
    def validate_observation(payload: dict) -> bool:
        try:
            Observation(**payload)
            return True
        except ValidationError as e:
            logger.error("fhir_validation_failed", errors=e.errors())
            return False
