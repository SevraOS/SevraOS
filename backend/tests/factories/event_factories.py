"""
HELIOS OS + SEVRA AI
Test Factories (factory-boy)

Provides model factories for generating test data.
Uses factory-boy with Faker for realistic clinical test data.
All factories produce dictionaries (framework-agnostic) until
SQLAlchemy models are defined in later prompts.
"""

from __future__ import annotations

import uuid
from datetime import timezone

import factory
from faker import Faker

from shared.utils.datetime_utils import utc_now

fake = Faker()


# ── Internal Event Envelope Factory ──────────────────────────────────────────

class InternalEventEnvelopeFactory(factory.Factory):
    """
    Generates valid Internal Event Envelopes.
    Used for testing Validation, Normalization, and downstream services.
    """

    class Meta:
        model = dict

    event_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    schema_version = "1.0.0"
    device_id = factory.LazyFunction(lambda: f"DEV-ICU-BED{fake.numerify('##')}-MONITOR")
    patient_id = factory.LazyFunction(lambda: f"PAT-{fake.numerify('#####')}")
    facility_id = "FACILITY-001"
    ward = factory.LazyFunction(lambda: fake.random_element(["ICU", "CCU", "WARD-A", "WARD-B"]))
    bed = factory.LazyFunction(lambda: fake.numerify("##"))
    received_at = factory.LazyFunction(lambda: utc_now().isoformat())
    source_protocol = factory.LazyFunction(
        lambda: fake.random_element(["HL7v2", "MQTT", "DICOM", "Serial", "FHIR", "Simulator"])
    )
    resolution_status = "resolved"
    payload = factory.LazyFunction(
        lambda: {
            "raw_observations": [
                {
                    "code": "8867-4",
                    "value": fake.random_int(min=60, max=100),
                    "unit": "/min",
                    "label": "Heart Rate",
                },
                {
                    "code": "59408-5",
                    "value": fake.random_int(min=94, max=100),
                    "unit": "%",
                    "label": "SpO2",
                },
            ]
        }
    )


# ── Specialized Envelope Variants ────────────────────────────────────────────

class UnresolvedPatientEnvelopeFactory(InternalEventEnvelopeFactory):
    """Envelope where patient_id could not be resolved."""
    patient_id = None
    resolution_status = "unresolved"


class CriticalVitalEnvelopeFactory(InternalEventEnvelopeFactory):
    """Envelope with clinically critical vital signs (triggers AI alerts)."""
    payload = factory.LazyFunction(
        lambda: {
            "raw_observations": [
                {"code": "8867-4", "value": 130, "unit": "/min", "label": "Heart Rate"},
                {"code": "59408-5", "value": 88, "unit": "%", "label": "SpO2"},
                {"code": "9279-1", "value": 26, "unit": "/min", "label": "Respiratory Rate"},
            ]
        }
    )


class InvalidVitalEnvelopeFactory(InternalEventEnvelopeFactory):
    """Envelope with physiologically impossible values (should fail validation)."""
    payload = factory.LazyFunction(
        lambda: {
            "raw_observations": [
                {"code": "8867-4", "value": 450, "unit": "/min", "label": "Heart Rate"},
            ]
        }
    )


# ── FHIR Observation Factory ──────────────────────────────────────────────────

class FHIRObservationFactory(factory.Factory):
    """Generates valid FHIR R4 Observation resources for testing."""

    class Meta:
        model = dict

    event_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    schema_version = "fhir-r4-1.0.0"
    normalized_at = factory.LazyFunction(lambda: utc_now().isoformat())
    fhir_resource = factory.LazyFunction(
        lambda: {
            "resourceType": "Observation",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate",
                }]
            },
            "subject": {"reference": f"Patient/PAT-{fake.numerify('#####')}"},
            "effectiveDateTime": utc_now().isoformat(),
            "valueQuantity": {
                "value": fake.random_int(min=60, max=100),
                "unit": "/min",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        }
    )


# ── AI Insight Factory ────────────────────────────────────────────────────────

class AIInsightFactory(factory.Factory):
    """Generates AI insight events for testing Dashboard and Hospital Integration."""

    class Meta:
        model = dict

    insight_id = factory.LazyFunction(lambda: f"ai-insight-{str(uuid.uuid4())[:8]}")
    patient_id = factory.LazyFunction(lambda: f"PAT-{fake.numerify('#####')}")
    model_id = "news2-calculator"
    model_version = "1.0.0"
    insight_type = "early_warning"
    severity = factory.LazyFunction(
        lambda: fake.random_element(["info", "warning", "critical"])
    )
    score = factory.LazyFunction(lambda: {"news2": fake.random_int(min=0, max=20)})
    confidence_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.7, max_value=1.0), 2))
    clinical_rationale = "Test insight generated by factory."
    triggered_by = factory.LazyFunction(lambda: [str(uuid.uuid4())])
    generated_at = factory.LazyFunction(lambda: utc_now().isoformat())
