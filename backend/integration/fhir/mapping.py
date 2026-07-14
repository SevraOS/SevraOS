"""
HELIOS OS + SEVRA AI
FHIR Observation Mapping (Section 4)
"""

from datetime import timezone
from typing import Dict, Any

from integration.fhir.models import Observation, CodeableConcept, Reference, Quantity
from normalization.canonical import CanonicalEvent

# LOINC Mapping for common vitals
LOINC_MAP = {
    "heart_rate": {"code": "8867-4", "display": "Heart rate", "unit": "/min"},
    "systolic_bp": {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mm[Hg]"},
    "diastolic_bp": {"code": "8462-4", "display": "Diastolic blood pressure", "unit": "mm[Hg]"},
    "spo2": {"code": "59408-5", "display": "Oxygen saturation in Arterial blood by Pulse oximetry", "unit": "%"},
    "temperature": {"code": "8310-5", "display": "Body temperature", "unit": "Cel"},
    "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate", "unit": "/min"}
}

class FHIRMapper:
    """Transforms internal schemas to FHIR resources."""
    
    @staticmethod
    def vital_to_observation(event: CanonicalEvent, ehr_patient_id: str) -> Observation:
        """Map a Helios Vital Event to a FHIR Observation."""
        
        mapping = LOINC_MAP.get(event.metric, {"code": "UNKNOWN", "display": event.metric, "unit": event.unit})
        
        code = CodeableConcept(
            coding=[{
                "system": "http://loinc.org",
                "code": mapping["code"],
                "display": mapping["display"]
            }],
            text=mapping["display"]
        )
        
        category = CodeableConcept(
            coding=[{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        )
        
        quantity = Quantity(
            value=event.value,
            unit=mapping["unit"],
            code=mapping["unit"]
        )
        
        return Observation(
            status="final",
            category=[category],
            code=code,
            subject=Reference(reference=f"Patient/{ehr_patient_id}"),
            effectiveDateTime=event.captured_at,
            valueQuantity=quantity,
            device=Reference(reference=f"Device/{event.source_device}") if event.source_device else None
        )
