"""
HELIOS OS + SEVRA AI
MDIL Unit Tests — Schema & RawReading

Tests:
  - RawReading construction and validation
  - DeviceType, MetricType, Unit enums
  - to_dict / from_dict round-trip
  - UTC enforcement
  - Edge cases
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from mdil.schema import (
    DeviceType,
    MetricType,
    RawReading,
    ReadingQuality,
    Unit,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_reading() -> RawReading:
    """Minimal valid RawReading."""
    return RawReading(
        device_type=DeviceType.ECG,
        device_id="ECG-TEST-001",
        captured_at=datetime.now(timezone.utc),
        metric=MetricType.HEART_RATE,
        value=72.0,
        unit=Unit.BPM,
        raw_payload="DAT|72|0.84|II",
    )


@pytest.fixture
def bytes_reading() -> RawReading:
    """RawReading with bytes raw_payload."""
    return RawReading(
        device_type=DeviceType.SPO2,
        device_id="SPO2-TEST-001",
        captured_at=datetime.now(timezone.utc),
        metric=MetricType.SPO2,
        value=98,
        unit=Unit.PERCENT,
        raw_payload=bytes([0x03, 0x62, 0x48, 0x00]),
    )


# ── Construction Tests ────────────────────────────────────────────────────────

class TestRawReadingConstruction:
    def test_minimal_fields_accepted(self, minimal_reading: RawReading) -> None:
        assert minimal_reading.device_type == DeviceType.ECG
        assert minimal_reading.device_id == "ECG-TEST-001"
        assert minimal_reading.metric == MetricType.HEART_RATE
        assert minimal_reading.value == 72.0
        assert minimal_reading.unit == Unit.BPM

    def test_reading_id_auto_generated(self, minimal_reading: RawReading) -> None:
        assert minimal_reading.reading_id is not None
        # Must be a valid UUID4
        parsed = uuid.UUID(minimal_reading.reading_id, version=4)
        assert str(parsed) == minimal_reading.reading_id

    def test_two_readings_have_different_ids(self) -> None:
        r1 = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.HEART_RATE, value=70.0,
            unit=Unit.BPM, raw_payload="DAT|70|0.8|II",
        )
        r2 = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.HEART_RATE, value=70.0,
            unit=Unit.BPM, raw_payload="DAT|70|0.8|II",
        )
        assert r1.reading_id != r2.reading_id

    def test_naive_datetime_gets_utc_tzinfo(self) -> None:
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)  # No tzinfo
        reading = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=naive_dt,
            metric=MetricType.HEART_RATE, value=72.0,
            unit=Unit.BPM, raw_payload="x",
        )
        assert reading.captured_at.tzinfo == timezone.utc

    def test_aware_datetime_preserved(self) -> None:
        aware_dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        reading = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=aware_dt,
            metric=MetricType.HEART_RATE, value=72.0,
            unit=Unit.BPM, raw_payload="x",
        )
        assert reading.captured_at == aware_dt

    def test_empty_device_id_raises(self) -> None:
        with pytest.raises(ValueError, match="device_id"):
            RawReading(
                device_type=DeviceType.ECG, device_id="",
                captured_at=datetime.now(timezone.utc),
                metric=MetricType.HEART_RATE, value=72.0,
                unit=Unit.BPM, raw_payload="x",
            )

    def test_whitespace_device_id_raises(self) -> None:
        with pytest.raises(ValueError, match="device_id"):
            RawReading(
                device_type=DeviceType.ECG, device_id="   ",
                captured_at=datetime.now(timezone.utc),
                metric=MetricType.HEART_RATE, value=72.0,
                unit=Unit.BPM, raw_payload="x",
            )

    def test_waveform_value_list_accepted(self) -> None:
        reading = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.ECG_WAVEFORM,
            value=[0.1, 0.2, 0.95, 1.02, 0.87],
            unit=Unit.MV, raw_payload="WFM|II|500|0.1,0.2",
            sampling_rate_hz=500.0,
        )
        assert isinstance(reading.value, list)
        assert len(reading.value) == 5

    def test_string_value_accepted(self) -> None:
        reading = RawReading(
            device_type=DeviceType.INFUSION_PUMP, device_id="INF-01",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.INFUSION_DRUG_NAME,
            value="Morphine", unit=Unit.UNITLESS, raw_payload="DRUG=Morphine",
        )
        assert reading.value == "Morphine"

    def test_metadata_default_is_empty_dict(self, minimal_reading: RawReading) -> None:
        assert minimal_reading.metadata == {}

    def test_quality_default_is_unknown(self, minimal_reading: RawReading) -> None:
        assert minimal_reading.quality == ReadingQuality.UNKNOWN


# ── Serialization Tests ───────────────────────────────────────────────────────

class TestRawReadingSerialization:
    def test_to_dict_returns_all_keys(self, minimal_reading: RawReading) -> None:
        d = minimal_reading.to_dict()
        required_keys = {
            "reading_id", "device_type", "device_id", "captured_at",
            "metric", "value", "unit", "raw_payload", "raw_payload_encoding",
            "facility_id", "ward", "bed", "quality",
            "sampling_rate_hz", "sequence_number", "metadata",
        }
        assert required_keys.issubset(d.keys())

    def test_to_dict_captured_at_is_iso_string(self, minimal_reading: RawReading) -> None:
        d = minimal_reading.to_dict()
        assert isinstance(d["captured_at"], str)
        # Must be parseable
        dt = datetime.fromisoformat(d["captured_at"])
        assert dt.tzinfo is not None

    def test_to_dict_bytes_payload_is_base64(self, bytes_reading: RawReading) -> None:
        d = bytes_reading.to_dict()
        assert d["raw_payload_encoding"] == "base64"
        decoded = base64.b64decode(d["raw_payload"])
        assert decoded == bytes([0x03, 0x62, 0x48, 0x00])

    def test_to_dict_string_payload_is_plain(self, minimal_reading: RawReading) -> None:
        d = minimal_reading.to_dict()
        assert d["raw_payload_encoding"] == "string"
        assert d["raw_payload"] == "DAT|72|0.84|II"

    def test_from_dict_round_trip_string_payload(self, minimal_reading: RawReading) -> None:
        d = minimal_reading.to_dict()
        restored = RawReading.from_dict(d)
        assert restored.device_type == minimal_reading.device_type
        assert restored.device_id == minimal_reading.device_id
        assert restored.metric == minimal_reading.metric
        assert restored.value == minimal_reading.value
        assert restored.unit == minimal_reading.unit
        assert restored.raw_payload == minimal_reading.raw_payload

    def test_from_dict_round_trip_bytes_payload(self, bytes_reading: RawReading) -> None:
        d = bytes_reading.to_dict()
        restored = RawReading.from_dict(d)
        assert isinstance(restored.raw_payload, bytes)
        assert restored.raw_payload == bytes_reading.raw_payload

    def test_from_dict_reading_id_preserved(self, minimal_reading: RawReading) -> None:
        d = minimal_reading.to_dict()
        restored = RawReading.from_dict(d)
        assert restored.reading_id == minimal_reading.reading_id

    def test_from_dict_metadata_preserved(self) -> None:
        reading = RawReading(
            device_type=DeviceType.ECG, device_id="D1",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.HEART_RATE, value=72.0,
            unit=Unit.BPM, raw_payload="x",
            metadata={"lead": "II", "firmware": "v1.2.3"},
        )
        restored = RawReading.from_dict(reading.to_dict())
        assert restored.metadata == {"lead": "II", "firmware": "v1.2.3"}


# ── Enum Tests ────────────────────────────────────────────────────────────────

class TestEnums:
    def test_device_type_values(self) -> None:
        assert DeviceType.ECG == "ecg"
        assert DeviceType.BLOOD_PRESSURE == "blood_pressure"
        assert DeviceType.SPO2 == "spo2"
        assert DeviceType.VENTILATOR == "ventilator"
        assert DeviceType.INFUSION_PUMP == "infusion_pump"
        assert DeviceType.GLUCOMETER == "glucometer"

    def test_unit_str_enum(self) -> None:
        assert Unit.BPM == "bpm"
        assert Unit.MMHG == "mmHg"
        assert Unit.PERCENT == "%"
        assert Unit.MV == "mV"

    def test_reading_quality_values(self) -> None:
        assert ReadingQuality.GOOD == "good"
        assert ReadingQuality.MARGINAL == "marginal"
        assert ReadingQuality.POOR == "poor"
        assert ReadingQuality.UNKNOWN == "unknown"
