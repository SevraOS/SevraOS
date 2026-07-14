"""
HELIOS OS + SEVRA AI
Blood Pressure Adapter

Parses BP monitor frames into RawReadings.

Supported frame format:
    SYS=120 DIA=80 MAP=93
    SYS=118 DIA=76 MAP=90 PR=72

Produces 3–4 RawReadings per frame:
    systolic_bp, diastolic_bp, mean_arterial_pressure, (optional) heart_rate
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Sequence

from mdil.base import DeviceAdapter, AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, RawReading, ReadingQuality, Unit

# Pattern: KEY=VALUE pairs separated by spaces
_KV_PATTERN = re.compile(r"(\w+)=([\d.]+)")


@AdapterRegistry.register
class BPAdapter(DeviceAdapter):
    """
    Blood Pressure Monitor Adapter.

    Parses key=value ASCII frames and produces systolic, diastolic,
    and MAP RawReadings. Optionally produces a pulse rate reading.
    """

    device_type = DeviceType.BLOOD_PRESSURE
    supported_protocols = ["Custom-KV-BP-v1"]
    adapter_version = "1.0.0"

    # Required fields in the frame
    _REQUIRED_KEYS = {"SYS", "DIA", "MAP"}

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        if isinstance(raw_frame, bytes):
            try:
                frame_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"BP frame is not valid ASCII: {exc}",
                    raw_frame=raw_frame,
                    device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            frame_str = raw_frame.strip()

        if not frame_str:
            return []

        # Parse all key=value pairs
        pairs = {k.upper(): v for k, v in _KV_PATTERN.findall(frame_str)}

        # Validate required keys
        missing = self._REQUIRED_KEYS - pairs.keys()
        if missing:
            raise AdapterParseError(
                f"BP frame missing required fields: {missing}. Frame: '{frame_str}'",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        # Parse numeric values
        try:
            sys_mmhg = float(pairs["SYS"])
            dia_mmhg = float(pairs["DIA"])
            map_mmhg = float(pairs["MAP"])
        except ValueError as exc:
            raise AdapterParseError(
                f"BP frame has non-numeric value: {exc}. Frame: '{frame_str}'",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        # Sanity range checks (physiological plausibility)
        self._check_range("SYS", sys_mmhg, 40, 300, raw_frame)
        self._check_range("DIA", dia_mmhg, 20, 200, raw_frame)
        self._check_range("MAP", map_mmhg, 20, 250, raw_frame)

        now = datetime.now(timezone.utc)
        readings: list[RawReading] = [
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.SYSTOLIC_BP,
                value=sys_mmhg,
                unit=Unit.MMHG,
                raw_payload=frame_str,
                quality=ReadingQuality.GOOD,
            ),
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.DIASTOLIC_BP,
                value=dia_mmhg,
                unit=Unit.MMHG,
                raw_payload=frame_str,
                quality=ReadingQuality.GOOD,
            ),
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.MEAN_ARTERIAL_PRESSURE,
                value=map_mmhg,
                unit=Unit.MMHG,
                raw_payload=frame_str,
                quality=ReadingQuality.GOOD,
            ),
        ]

        # Optional pulse rate
        if "PR" in pairs:
            try:
                pr = float(pairs["PR"])
                self._check_range("PR", pr, 0, 300, raw_frame)
                readings.append(
                    RawReading(
                        device_type=self.device_type,
                        device_id=self.device_id,
                        captured_at=now,
                        metric=MetricType.HEART_RATE,
                        value=pr,
                        unit=Unit.BPM,
                        raw_payload=frame_str,
                        quality=ReadingQuality.GOOD,
                        metadata={"source": "bp_monitor_pr"},
                    )
                )
            except ValueError:
                pass  # PR field present but non-numeric — skip

        return readings

    def _check_range(
        self,
        field: str,
        value: float,
        min_val: float,
        max_val: float,
        raw_frame: str | bytes,
    ) -> None:
        if not (min_val <= value <= max_val):
            raise AdapterParseError(
                f"BP field '{field}'={value} is outside physiological range [{min_val}, {max_val}].",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )
