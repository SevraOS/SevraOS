"""
HELIOS OS + SEVRA AI
Integration Tests (Section 23)
"""

import pytest
from datetime import datetime, timezone
from integration.fhir.models import Observation
from integration.fhir.mapping import FHIRMapper
from normalization.canonical import CanonicalEvent

def test_fhir_vital_mapping():
    """Verify CanonicalEvent maps perfectly to FHIR R4 Observation."""
    event = CanonicalEvent(
        client_event_id="evt-123",
        patient_id="helios-pt-1",
        metric="heart_rate",
        value=85.0,
        unit="bpm",
        loinc="8867-4",
        captured_at=datetime.now(timezone.utc),
        source_device="dev-456",
        flagged=False
    )
    
    observation = FHIRMapper.vital_to_observation(event, "epic-mrn-789")
    
    assert observation.resourceType == "Observation"
    assert observation.status == "final"
    assert observation.valueQuantity.value == 85.0
    assert observation.subject.reference == "Patient/epic-mrn-789"
    assert "8867-4" in observation.code.coding[0]["code"] # LOINC for HR

def test_hl7_adt_parser():
    """Verify legacy HL7 v2 parser extracts correct PID."""
    from integration.hl7.parser import HL7Parser
    
    msg = "MSH|^~\\&|EPIC|HOSP|||20231010120000||ADT^A01|MSG001|P|2.5\rPID|1||MRN12345||SMITH^JOHN||19800101|M\rPV1|1|I|ICU^BED1"
    parser = HL7Parser()
    parsed = parser.parse_adt(msg)
    
    assert parsed["msh"]["sending_app"] == "EPIC"
    assert parsed["pid"]["patient_id"] == "MRN12345"
    assert parsed["pid"]["name"] == "SMITH^JOHN"
