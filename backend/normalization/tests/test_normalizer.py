import pytest
from datetime import datetime, timezone
from mdil.schema import RawReading, MetricType, Unit
from validation.result import ValidationResult, ValidationStatus, ValidationReason, ValidationMetadata
from normalization.normalizer import NormalizerEngine
from normalization.canonical import CanonicalEvent
from normalization.fhir_projection import FHIRProjector

@pytest.fixture
def normalizer():
    return NormalizerEngine()

@pytest.fixture
def valid_result():
    reading = RawReading(
        device_id="SIM-ECG-001",
        device_type="ecg",
        metric=MetricType.HEART_RATE,
        value=75.0,
        unit=Unit.BPM,
        captured_at=datetime.now(timezone.utc),
        raw_payload=b"test"
    )
    meta = ValidationMetadata(
        device_id="SIM-ECG-001",
        metric=MetricType.HEART_RATE,
        reason=ValidationReason.VALID,
        severity="info"
    )
    return ValidationResult(
        status=ValidationStatus.ACCEPTED,
        reason=ValidationReason.VALID,
        metadata=meta,
        original_reading=reading
    )

# --- Schema & Resolution Tests ---
def test_normalization_success(normalizer, valid_result):
    event, error = normalizer.normalize(valid_result)
    assert error is None
    assert isinstance(event, CanonicalEvent)
    assert event.patient_id == "PAT-1001" # Matches patient_resolution.py
    assert event.loinc == "8867-4"
    assert event.value == 75.0
    assert event.unit == "bpm"
    assert event.flagged is False
    assert event.client_event_id is not None

def test_normalization_drops_unassigned_device(normalizer, valid_result):
    valid_result.original_reading.device_id = "UNKNOWN-999"
    event, error = normalizer.normalize(valid_result)
    assert event is None
    assert error == "unassigned_device"

def test_normalization_drops_rejected(normalizer, valid_result):
    valid_result.status = ValidationStatus.REJECTED
    event, error = normalizer.normalize(valid_result)
    assert event is None
    assert error == "rejected_by_validation"

def test_normalization_flags_outliers(normalizer, valid_result):
    valid_result.status = ValidationStatus.FLAGGED
    event, error = normalizer.normalize(valid_result)
    assert error is None
    assert event.flagged is True

# --- Conversion Tests ---
def test_normalization_temperature_conversion(normalizer, valid_result):
    valid_result.original_reading.metric = MetricType.BODY_TEMPERATURE
    valid_result.original_reading.value = 100.4
    valid_result.original_reading.unit = "F"
    event, error = normalizer.normalize(valid_result)
    assert error is None
    assert event.value == 38.0  # 100.4 F -> 38.0 C
    assert event.unit == Unit.CELSIUS.value
    assert event.loinc == "8310-5"

def test_normalization_glucose_conversion(normalizer, valid_result):
    valid_result.original_reading.metric = MetricType.BLOOD_GLUCOSE
    valid_result.original_reading.value = 100.0
    valid_result.original_reading.unit = "mg/dL"
    event, error = normalizer.normalize(valid_result)
    assert error is None
    assert event.value == 5.55  # 100.0 / 18.0182 -> ~5.55
    assert event.unit == Unit.MMOL_PER_L.value

# --- LOINC Mapping Tests ---
def test_normalization_drops_missing_loinc(normalizer, valid_result):
    # Pass a metric that is not mapped in LOINCMapper
    valid_result.original_reading.metric = "unknown_metric"
    event, error = normalizer.normalize(valid_result)
    assert event is None
    assert error == "missing_loinc_mapping"

# --- FHIR Projection Tests ---
def test_fhir_projection(normalizer, valid_result):
    event, _ = normalizer.normalize(valid_result)
    
    fhir_obs = FHIRProjector.project(event)
    
    assert fhir_obs["resourceType"] == "Observation"
    assert fhir_obs["status"] == "final"
    assert fhir_obs["code"]["coding"][0]["code"] == "8867-4"
    assert fhir_obs["subject"]["reference"] == "Patient/PAT-1001"
    assert fhir_obs["valueQuantity"]["value"] == 75.0
    assert fhir_obs["device"]["reference"] == "Device/SIM-ECG-001"
    assert len(fhir_obs["meta"]["tag"]) == 0

def test_fhir_projection_flagged(normalizer, valid_result):
    valid_result.status = ValidationStatus.FLAGGED
    event, _ = normalizer.normalize(valid_result)
    
    fhir_obs = FHIRProjector.project(event)
    assert len(fhir_obs["meta"]["tag"]) == 1
    assert fhir_obs["meta"]["tag"][0]["code"] == "flagged"
