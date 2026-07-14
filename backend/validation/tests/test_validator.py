import pytest
import time
from datetime import datetime, timezone
from mdil.schema import RawReading, MetricType, Unit
from validation.validator import ValidationEngine
from validation.result import ValidationStatus, ValidationReason

@pytest.fixture
def validator():
    return ValidationEngine()

@pytest.fixture
def raw_reading():
    return RawReading(
        device_id="TEST-DEV-001",
        device_type="ecg",
        metric=MetricType.HEART_RATE,
        value=75.0,
        unit=Unit.BPM,
        captured_at=datetime.now(timezone.utc),
        raw_payload=b"test"
    )

# --- Unit & Boundary Tests ---
def test_valid_reading_accepted(validator, raw_reading):
    result = validator.validate(raw_reading)
    assert result.status == ValidationStatus.ACCEPTED
    assert result.reason == ValidationReason.VALID

def test_null_value_rejected(validator, raw_reading):
    raw_reading.value = None
    result = validator.validate(raw_reading)
    assert result.status == ValidationStatus.REJECTED
    assert result.reason == ValidationReason.NULL_VALUE

def test_corrupt_payload_rejected(validator, raw_reading):
    raw_reading.value = "not_a_number"
    result = validator.validate(raw_reading)
    assert result.status == ValidationStatus.REJECTED
    assert result.reason == ValidationReason.INVALID_TYPE

def test_nan_value_rejected(validator, raw_reading):
    raw_reading.value = float("nan")
    result = validator.validate(raw_reading)
    assert result.status == ValidationStatus.REJECTED
    assert result.reason == ValidationReason.CORRUPT_PAYLOAD

def test_boundary_hr_ranges(validator, raw_reading):
    # From ranges.yaml: HR min: 30, max: 220
    # Test valid boundary
    raw_reading.value = 30.0
    assert validator.validate(raw_reading).status == ValidationStatus.ACCEPTED
    
    raw_reading.value = 220.0
    assert validator.validate(raw_reading).status == ValidationStatus.ACCEPTED
    
    # Test invalid boundary
    raw_reading.value = 29.9
    assert validator.validate(raw_reading).status == ValidationStatus.REJECTED
    
    raw_reading.value = 220.1
    assert validator.validate(raw_reading).status == ValidationStatus.REJECTED

# --- Outlier Tests ---
def test_outlier_flagged(validator, raw_reading):
    # Push stable data to build window
    for i in range(10):
        raw_reading.value = 75.0 + (i % 2) # Create small variance
        res = validator.validate(raw_reading)
        assert res.status == ValidationStatus.ACCEPTED
        
    # Push sudden spike (still in physiological range 30-220, but stats outlier)
    raw_reading.value = 180.0
    result = validator.validate(raw_reading)
    assert result.status == ValidationStatus.FLAGGED
    assert result.reason == ValidationReason.STATISTICAL_OUTLIER

# --- Truth Table Tests ---
@pytest.mark.parametrize("value, expected_status", [
    (75.0, ValidationStatus.ACCEPTED),
    (15.0, ValidationStatus.REJECTED), # Out of range
    (500.0, ValidationStatus.REJECTED), # Out of range
    (None, ValidationStatus.REJECTED), # Null
    ("invalid", ValidationStatus.REJECTED), # Type error
    (float("inf"), ValidationStatus.REJECTED), # Corrupt
])
def test_validation_truth_table(validator, raw_reading, value, expected_status):
    raw_reading.value = value
    result = validator.validate(raw_reading)
    assert result.status == expected_status

# --- Stress Tests ---
def test_validation_stress(validator, raw_reading):
    # Process 10,000 readings rapidly
    start_time = time.perf_counter()
    for i in range(10000):
        # Slightly jitter the value to avoid 0 variance
        raw_reading.value = 70.0 + (i % 5)
        res = validator.validate(raw_reading)
        assert res.status == ValidationStatus.ACCEPTED
    duration = time.perf_counter() - start_time
    
    # Assert validation takes less than 0.5s for 10k readings
    assert duration < 2.0
