"""
HELIOS OS + SEVRA AI
Glucometer Adapter

Parses glucose meter frames into RawReadings.

Supported ASCII frame formats:
    Format A (USB/Serial): GLU=7.2 UNIT=mmol/L MID=before_meal SN=00234
    Format B (mg/dL):      GLU=130 UNIT=mg/dL MID=after_meal SN=00235
    Format C (compact):    G=7.4 U=mmol/L
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

_KV_PATTERN = re.compile(r"(\w+)=([^\s]+)")

# Measurement ID (meal timing) mapping
_MEAL_TIMING_MAP = {
    "before_meal": "pre-meal",
    "after_meal": "post-meal",
    "fasting": "fasting",
    "bedtime": "bedtime",
    "random": "random",
}

# Physiological plausibility ranges
_GLU_MMOL_MIN = 0.5
_GLU_MMOL_MAX = 33.3
_GLU_MGDL_MIN = 10.0
_GLU_MGDL_MAX = 600.0


@AdapterRegistry.register
class GlucometerAdapter(DeviceAdapter):
    """
    Glucometer Adapter.

    Parses ASCII glucose measurement frames.
    Supports mmol/L and mg/dL units.
    Produces one RawReading per frame (blood_glucose metric).
    """

    device_type = DeviceType.GLUCOMETER
    supported_protocols = ["Custom-KV-Glucose-v1"]
    adapter_version = "1.0.0"

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        if isinstance(raw_frame, bytes):
            try:
                frame_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"Glucometer frame decode error: {exc}",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            frame_str = raw_frame.strip()

        if not frame_str:
            return []

        pairs = {k.upper(): v for k, v in _KV_PATTERN.findall(frame_str)}

        # Support compact G= form
        glu_key = "GLU" if "GLU" in pairs else ("G" if "G" in pairs else None)
        unit_key = "UNIT" if "UNIT" in pairs else ("U" if "U" in pairs else None)

        if glu_key is None:
            raise AdapterParseError(
                f"Glucometer frame missing glucose value (GLU= or G=). Frame: '{frame_str}'",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            glu_value = float(pairs[glu_key])
        except ValueError:
            raise AdapterParseError(
                f"Glucometer GLU value non-numeric: '{pairs[glu_key]}'",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        # Determine unit
        unit_str = pairs.get(unit_key, "mmol/L") if unit_key else "mmol/L"
        unit_str_lower = unit_str.lower().replace(" ", "")

        if unit_str_lower in ("mmol/l", "mmol"):
            unit = Unit.MMOL_PER_L
            if not (_GLU_MMOL_MIN <= glu_value <= _GLU_MMOL_MAX):
                raise AdapterParseError(
                    f"Glucose {glu_value} mmol/L outside range "
                    f"[{_GLU_MMOL_MIN}, {_GLU_MMOL_MAX}].",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
        elif unit_str_lower in ("mg/dl", "mgdl", "mg/dl"):
            unit = Unit.MG_PER_DL
            if not (_GLU_MGDL_MIN <= glu_value <= _GLU_MGDL_MAX):
                raise AdapterParseError(
                    f"Glucose {glu_value} mg/dL outside range "
                    f"[{_GLU_MGDL_MIN}, {_GLU_MGDL_MAX}].",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            self._log.warning("glucometer_unknown_unit", unit=unit_str)
            unit = Unit.UNKNOWN

        # Extract optional metadata
        meal_raw = pairs.get("MID", "").lower()
        meal_timing = _MEAL_TIMING_MAP.get(meal_raw, meal_raw or None)
        serial_num = pairs.get("SN")

        metadata: dict = {"unit_raw": unit_str}
        if meal_timing:
            metadata["meal_timing"] = meal_timing
        if serial_num:
            metadata["device_serial"] = serial_num

        return [
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=datetime.now(timezone.utc),
                metric=MetricType.BLOOD_GLUCOSE,
                value=glu_value,
                unit=unit,
                raw_payload=frame_str,
                quality=ReadingQuality.GOOD,
                metadata=metadata,
            )
        ]
