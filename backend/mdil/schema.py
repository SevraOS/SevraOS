"""
HELIOS OS + SEVRA AI
MDIL Schema — RawReading Contract

RawReading is the single output type of every device adapter.
It is the canonical internal format that exits the MDIL and
enters the Collector → Validation → Normalization pipeline.

Contract rules:
  - Every field is typed — no bare dicts or untyped Any for clinical fields
  - captured_at is always UTC
  - raw_payload preserves the original bytes/string for audit purposes
  - metadata carries device-level context (ward, bed, facility)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Device Type Enumeration ───────────────────────────────────────────────────

class DeviceType(str, Enum):
    """
    Canonical device type identifiers.
    Used across MDIL, Collectors, Validation, and AI Service.
    """
    ECG = "ecg"
    BLOOD_PRESSURE = "blood_pressure"
    SPO2 = "spo2"
    VENTILATOR = "ventilator"
    INFUSION_PUMP = "infusion_pump"
    GLUCOMETER = "glucometer"
    TEMPERATURE = "temperature"
    WEIGHT_SCALE = "weight_scale"
    SIMULATOR = "simulator"
    UNKNOWN = "unknown"


# ── Metric Identifier Enumeration ─────────────────────────────────────────────

class MetricType(str, Enum):
    """
    Canonical metric names aligned with LOINC code semantics.
    Used to map RawReading.metric → LOINC code in Normalization.
    """
    # Cardiac
    HEART_RATE = "heart_rate"
    ECG_LEAD_I = "ecg_lead_i"
    ECG_LEAD_II = "ecg_lead_ii"
    ECG_LEAD_III = "ecg_lead_iii"
    ECG_WAVEFORM = "ecg_waveform"
    QRS_DURATION = "qrs_duration"
    PR_INTERVAL = "pr_interval"
    QT_INTERVAL = "qt_interval"
    PULSE_RATE = "pulse_rate"
    PERFUSION_INDEX = "perfusion_index"

    # Hemodynamic
    SYSTOLIC_BP = "systolic_bp"
    DIASTOLIC_BP = "diastolic_bp"
    MEAN_ARTERIAL_PRESSURE = "mean_arterial_pressure"

    # Respiratory / Oxygenation
    SPO2 = "spo2"
    RESPIRATORY_RATE = "respiratory_rate"
    TIDAL_VOLUME = "tidal_volume"
    PEAK_INSPIRATORY_PRESSURE = "peak_inspiratory_pressure"
    POSITIVE_END_EXPIRATORY_PRESSURE = "peep"
    FIO2 = "fio2"
    MINUTE_VENTILATION = "minute_ventilation"
    COMPLIANCE = "compliance"
    RESPIRATORY_RATE_VENT = "respiratory_rate_vent"
    PEEP = "peep"

    # Metabolic
    BLOOD_GLUCOSE = "blood_glucose"
    BODY_TEMPERATURE = "body_temperature"

    # Infusion
    INFUSION_FLOW_RATE = "infusion_flow_rate"
    INFUSION_VOLUME_DELIVERED = "infusion_volume_delivered"
    INFUSION_VOLUME_REMAINING = "infusion_volume_remaining"
    INFUSION_DRUG_NAME = "infusion_drug_name"
    INFUSION_CONCENTRATION = "infusion_concentration"
    INFUSION_RATE = "infusion_rate"
    VOLUME_INFUSED = "volume_infused"


# ── Unit Enumeration ──────────────────────────────────────────────────────────

class Unit(str, Enum):
    """Raw device units — mapped to UCUM in Normalization Service."""
    BPM = "bpm"
    MMHG = "mmHg"
    PERCENT = "%"
    MV = "mV"
    MS = "ms"
    ML = "mL"
    ML_PER_MIN = "mL/min"
    ML_PER_HOUR = "mL/h"
    CM_H2O = "cmH2O"
    MG_PER_DL = "mg/dL"
    MMOL_PER_L = "mmol/L"
    BREATHS_PER_MIN = "breaths/min"
    L_PER_MIN = "L/min"
    CELSIUS = "Cel"
    UNITLESS = ""
    UNKNOWN = "unknown"


# ── Device Reading Quality ────────────────────────────────────────────────────

class ReadingQuality(str, Enum):
    """Signal quality indicator set by the device adapter."""
    GOOD = "good"           # Device confirms good signal
    MARGINAL = "marginal"   # Acceptable but borderline
    POOR = "poor"           # Low confidence — flag for clinical review
    UNKNOWN = "unknown"     # Device does not report quality


# ── RawReading — The MDIL Output Contract ─────────────────────────────────────

@dataclass
class RawReading:
    """
    The canonical output of every DeviceAdapter.

    This is the only type that exits the MDIL.
    Downstream services (Collectors, Validation, Normalization) operate on RawReadings.

    Immutability: treat as immutable after creation. Do not mutate fields.
    Extensibility: use the metadata dict for device-specific extra fields.
                   Never add clinical fields to metadata — use typed fields only.
    """

    # ── Required fields ────────────────────────────────────────────────────
    device_type: DeviceType
    """Canonical device category (ecg, blood_pressure, etc.)"""

    device_id: str
    """Unique device identifier from the Device Registry."""

    captured_at: datetime
    """Timestamp when the device captured this reading. Always UTC."""

    metric: MetricType
    """The specific clinical metric being reported."""

    value: float | int | str | list[float]
    """
    The measured value.
    float: for scalar measurements (HR, BP, SpO2)
    list[float]: for waveform samples (ECG lead data)
    str: for categorical values (device status, drug name)
    """

    unit: Unit
    """The unit of measurement as reported by the device."""

    raw_payload: str | bytes
    """
    The original, unmodified payload from the device.
    Preserved for audit trail and re-processing capability.
    """

    # ── Derived / Optional fields ───────────────────────────────────────────
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Globally unique reading ID. Assigned by the adapter."""

    facility_id: str = field(default="FACILITY-001")
    """Facility where the device is located."""

    ward: str | None = field(default=None)
    """Ward identifier (ICU, CCU, WARD-A, etc.)"""

    bed: str | None = field(default=None)
    """Bed identifier within the ward."""

    quality: ReadingQuality = field(default=ReadingQuality.UNKNOWN)
    """Signal quality reported by the device or inferred by the adapter."""

    sampling_rate_hz: float | None = field(default=None)
    """For waveform data: samples per second (e.g., 500.0 Hz for ECG)."""

    sequence_number: int | None = field(default=None)
    """
    Device-assigned sequence number (if supported).
    Used to detect missed frames and ordering issues.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Adapter-specific supplementary data.
    Use for device model, firmware version, calibration date, etc.
    Do NOT put clinical values here — use typed metric fields only.
    """

    def __post_init__(self) -> None:
        """Validate and normalize fields after construction."""
        # Ensure captured_at is always UTC-aware
        if self.captured_at.tzinfo is None:
            self.captured_at = self.captured_at.replace(tzinfo=timezone.utc)

        # Validate device_id is non-empty
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id must be a non-empty string.")

        # Validate reading_id is non-empty
        if not self.reading_id:
            self.reading_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the RawReading to a dict for transmission to the Collector.
        captured_at is serialized to UTC ISO-8601 string.
        raw_payload bytes are base64-encoded.
        """
        import base64

        payload: str
        if isinstance(self.raw_payload, bytes):
            payload = base64.b64encode(self.raw_payload).decode("ascii")
        else:
            payload = self.raw_payload

        return {
            "reading_id": self.reading_id,
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "captured_at": self.captured_at.isoformat(),
            "metric": self.metric.value,
            "value": self.value,
            "unit": self.unit.value,
            "raw_payload": payload,
            "raw_payload_encoding": "base64" if isinstance(self.raw_payload, bytes) else "string",
            "facility_id": self.facility_id,
            "ward": self.ward,
            "bed": self.bed,
            "quality": self.quality.value,
            "sampling_rate_hz": self.sampling_rate_hz,
            "sequence_number": self.sequence_number,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawReading":
        """Deserialize a RawReading from a dict produced by to_dict()."""
        import base64
        from datetime import datetime

        raw_payload: str | bytes = data["raw_payload"]
        if data.get("raw_payload_encoding") == "base64":
            raw_payload = base64.b64decode(raw_payload)

        return cls(
            reading_id=data.get("reading_id", str(uuid.uuid4())),
            device_type=DeviceType(data["device_type"]),
            device_id=data["device_id"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
            metric=MetricType(data["metric"]),
            value=data["value"],
            unit=Unit(data["unit"]),
            raw_payload=raw_payload,
            facility_id=data.get("facility_id", "FACILITY-001"),
            ward=data.get("ward"),
            bed=data.get("bed"),
            quality=ReadingQuality(data.get("quality", "unknown")),
            sampling_rate_hz=data.get("sampling_rate_hz"),
            sequence_number=data.get("sequence_number"),
            metadata=data.get("metadata", {}),
        )
