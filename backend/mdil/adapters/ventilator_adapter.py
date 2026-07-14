"""
HELIOS OS + SEVRA AI
Ventilator Adapter

Parses HL7 v2.x ORU^R01 messages from mechanical ventilators.
Extracts respiratory mechanics metrics as RawReadings.

Supported HL7 OBX observation identifiers (OBX.3):
    59408-5   → SpO2
    9279-1    → Respiratory Rate
    76222-9   → Tidal Volume
    76002-5   → Peak Inspiratory Pressure
    76003-3   → PEEP
    250774007 → FiO2
    60842-2   → Minute Ventilation
    251980002 → Compliance
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Sequence

import structlog

from mdil.base import DeviceAdapter, AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, RawReading, ReadingQuality, Unit

logger = structlog.get_logger(__name__)

# Map HL7 OBX.3 LOINC/SNOMED codes → (MetricType, Unit)
_OBX_CODE_MAP: dict[str, tuple[MetricType, Unit]] = {
    "59408-5": (MetricType.SPO2, Unit.PERCENT),
    "9279-1": (MetricType.RESPIRATORY_RATE, Unit.BREATHS_PER_MIN),
    "76222-9": (MetricType.TIDAL_VOLUME, Unit.ML),
    "76002-5": (MetricType.PEAK_INSPIRATORY_PRESSURE, Unit.CM_H2O),
    "76003-3": (MetricType.POSITIVE_END_EXPIRATORY_PRESSURE, Unit.CM_H2O),
    "250774007": (MetricType.FIO2, Unit.PERCENT),
    "60842-2": (MetricType.MINUTE_VENTILATION, Unit.L_PER_MIN),
    "251980002": (MetricType.COMPLIANCE, Unit.UNITLESS),
    "8867-4": (MetricType.HEART_RATE, Unit.BPM),
}


@AdapterRegistry.register
class VentilatorAdapter(DeviceAdapter):
    """
    Mechanical Ventilator Adapter.

    Parses HL7 v2.x ORU^R01 messages using a field-by-field parser.
    Each OBX segment becomes one RawReading if the code is recognized.
    Unrecognized OBX codes are logged as debug and skipped.
    """

    device_type = DeviceType.VENTILATOR
    supported_protocols = ["HL7v2-ORU-R01"]
    adapter_version = "1.0.0"

    # HL7 field separator (default: |)
    FIELD_SEP = "|"
    # HL7 component separator (default: ^)
    COMP_SEP = "^"
    # HL7 segment terminator
    SEG_TERM = "\r"

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        """Parse an HL7 v2.x ORU^R01 message."""
        if isinstance(raw_frame, bytes):
            try:
                hl7_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"Ventilator HL7 frame decode error: {exc}",
                    raw_frame=raw_frame,
                    device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            hl7_str = raw_frame.strip()

        if not hl7_str:
            return []

        # Split into segments
        segments = [s.strip() for s in hl7_str.split(self.SEG_TERM) if s.strip()]

        if not segments:
            return []

        # Validate MSH segment
        if not segments[0].startswith("MSH"):
            raise AdapterParseError(
                f"HL7 message does not start with MSH segment.",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        readings: list[RawReading] = []
        device_metadata = self._extract_device_metadata(segments)

        for segment in segments:
            if not segment.startswith("OBX"):
                continue
            try:
                reading = self._parse_obx_segment(segment, hl7_str, device_metadata)
                if reading:
                    readings.append(reading)
            except AdapterParseError:
                raise
            except Exception as exc:
                self._log.warning("ventilator_obx_parse_error", segment=segment[:80], error=str(exc))

        return readings

    def _parse_obx_segment(
        self,
        segment: str,
        raw: str,
        device_metadata: dict,
    ) -> RawReading | None:
        """
        Parse a single OBX segment.

        OBX structure (1-indexed):
          1: Set ID
          2: Value Type (NM=numeric, ST=string, etc.)
          3: Observation Identifier (code^description^system)
          4: Observation Sub-ID
          5: Observation Value
          6: Units
          ...
        """
        fields = segment.split(self.FIELD_SEP)
        if len(fields) < 6:
            return None  # Malformed OBX — skip

        value_type = fields[2] if len(fields) > 2 else "NM"
        obs_identifier = fields[3] if len(fields) > 3 else ""
        obs_code = obs_identifier.split(self.COMP_SEP)[0].strip()
        obs_value_raw = fields[5] if len(fields) > 5 else ""

        if obs_code not in _OBX_CODE_MAP:
            self._log.debug("ventilator_unknown_obx_code", code=obs_code)
            return None

        metric_type, default_unit = _OBX_CODE_MAP[obs_code]

        # Parse observation timestamp from OBX-14 if available
        obs_datetime = datetime.now(timezone.utc)
        if len(fields) > 14 and fields[14]:
            try:
                obs_datetime = self._parse_hl7_datetime(fields[14])
            except ValueError:
                pass

        # Parse numeric value
        try:
            value: float | int | str = float(obs_value_raw.replace(",", "."))
        except ValueError:
            value = obs_value_raw  # Keep as string for categorical values

        return RawReading(
            device_type=self.device_type,
            device_id=self.device_id,
            captured_at=obs_datetime,
            metric=metric_type,
            value=value,
            unit=default_unit,
            raw_payload=raw,
            quality=ReadingQuality.GOOD,
            metadata={
                "hl7_obs_code": obs_code,
                "hl7_value_type": value_type,
                **device_metadata,
            },
        )

    def _extract_device_metadata(self, segments: list[str]) -> dict:
        """Extract device identification from MSH and OBR segments."""
        metadata: dict = {}
        for seg in segments:
            if seg.startswith("MSH"):
                fields = seg.split(self.FIELD_SEP)
                metadata["hl7_sending_application"] = fields[3] if len(fields) > 3 else ""
                metadata["hl7_sending_facility"] = fields[4] if len(fields) > 4 else ""
            elif seg.startswith("PID"):
                fields = seg.split(self.FIELD_SEP)
                if len(fields) > 3:
                    metadata["patient_id_hl7"] = fields[3]
        return metadata

    @staticmethod
    def _parse_hl7_datetime(hl7_dt: str) -> datetime:
        """
        Parse HL7 datetime string to UTC datetime.
        Formats: YYYYMMDDHHMMSS or YYYYMMDDHHMM or YYYYMMDD
        """
        hl7_dt = hl7_dt.strip()
        fmt_map = [
            ("%Y%m%d%H%M%S", 14),
            ("%Y%m%d%H%M", 12),
            ("%Y%m%d", 8),
        ]
        for fmt, length in fmt_map:
            if len(hl7_dt) >= length:
                try:
                    dt = datetime.strptime(hl7_dt[:length], fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        raise ValueError(f"Cannot parse HL7 datetime: '{hl7_dt}'")
