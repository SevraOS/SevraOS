from typing import Dict, Any
from normalization.canonical import CanonicalEvent

class FHIRProjector:
    """
    Projects CanonicalEvent to FHIR R4 Observation resource.
    """
    
    @staticmethod
    def project(event: CanonicalEvent) -> Dict[str, Any]:
        """Convert canonical event to FHIR Observation dictionary."""
        return {
            "resourceType": "Observation",
            "id": event.client_event_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": event.loinc,
                        "display": event.metric
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{event.patient_id}"
            },
            "effectiveDateTime": event.captured_at.isoformat(),
            "valueQuantity": {
                "value": event.value,
                "unit": event.unit,
                "system": "http://unitsofmeasure.org",
                "code": event.unit
            },
            "device": {
                "reference": f"Device/{event.source_device}"
            },
            "meta": {
                "tag": [
                    {
                        "system": "http://sevra.ai/flags",
                        "code": "flagged",
                        "display": "Statistically Anomalous"
                    }
                ] if event.flagged else []
            }
        }
