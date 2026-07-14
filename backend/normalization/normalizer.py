import structlog
from typing import Optional, Tuple
from validation.result import ValidationResult, ValidationStatus
from normalization.canonical import CanonicalEvent
from normalization.units import UnitConversionEngine
from normalization.loinc import LOINCMapper
from normalization.patient_resolution import PatientResolutionService

logger = structlog.get_logger(__name__)

class NormalizerEngine:
    """
    Transforms Validated Readings into Canonical Events.
    Applies Unit Conversions, LOINC mappings, and Patient Resolution.
    """
    
    def __init__(self):
        self.unit_converter = UnitConversionEngine()
        self.patient_resolver = PatientResolutionService()
        self.loinc_mapper = LOINCMapper()
        
    def normalize(self, result: ValidationResult) -> Tuple[Optional[CanonicalEvent], Optional[str]]:
        """
        Takes a ValidationResult (which wraps a RawReading).
        Returns (CanonicalEvent, None) on success.
        Returns (None, error_reason) if dropped (e.g. no patient found or missing LOINC mapping).
        """
        # 1. Ensure it's accepted or flagged
        if result.status == ValidationStatus.REJECTED:
            return None, "rejected_by_validation"
            
        reading = result.original_reading
        device_id = reading.device_id
        
        # 2. Patient Resolution
        patient_id = self.patient_resolver.resolve(device_id)
        if not patient_id:
            logger.debug("normalization_dropped_no_patient", device_id=device_id)
            return None, "unassigned_device"
            
        # 3. Unit Conversion
        numeric_value = float(reading.value)
        converted_value, standard_unit = self.unit_converter.convert(numeric_value, reading.unit)
        
        # 4. LOINC Mapping
        loinc_code = self.loinc_mapper.get_loinc(reading.metric)
        if not loinc_code:
            logger.warning("normalization_dropped_no_loinc", metric=reading.metric)
            return None, "missing_loinc_mapping"
            
        # 5. Construct Canonical Event
        event = CanonicalEvent(
            patient_id=patient_id,
            metric=reading.metric,
            value=converted_value,
            unit=standard_unit,
            loinc=loinc_code,
            captured_at=reading.captured_at,
            source_device=device_id,
            flagged=(result.status == ValidationStatus.FLAGGED),
            metadata=result.metadata.audit_data
        )
        
        return event, None
