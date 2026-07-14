"""
HELIOS OS + SEVRA AI
SpO2 Adapter

Parses pulse oximeter frames into RawReadings.
Supports both BLE binary payload and ASCII formats.

BLE binary payload (4 bytes):
    Byte 0: Flags
    Byte 1: SpO2 percentage (0–100)
    Byte 2: Heart rate (lower byte)
    Byte 3: Heart rate (upper byte, if multi-byte HR flag set)

ASCII format:
    SPO2=98 PR=72 PI=3.5 SQ=good
    SPO2=96 PR=68
"""

from __future__ import annotations

import re
import struct
from datetime import datetime, timezone
from typing import Sequence

from mdil.base import DeviceAdapter, AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, RawReading, ReadingQuality, Unit

_KV_PATTERN = re.compile(r"(\w+)=([\d.A-Za-z]+)")

# BLE SpO2 protocol flags (byte 0)
_FLAG_HR_16BIT = 0x01      # Heart rate is 16-bit (2 bytes)
_FLAG_SENSOR_CONTACT = 0x02  # Sensor contact detected
_FLAG_ENERGY_EXPENDED = 0x04
_FLAG_RR_INTERVAL = 0x08

# Quality string mapping
_QUALITY_MAP = {
    "good": ReadingQuality.GOOD,
    "marginal": ReadingQuality.MARGINAL,
    "poor": ReadingQuality.POOR,
    "unknown": ReadingQuality.UNKNOWN,
}


@AdapterRegistry.register
class SpO2Adapter(DeviceAdapter):
    """
    Pulse Oximeter Adapter.

    Supports:
      - BLE binary payload (GATT Heart Rate Measurement characteristic + custom SpO2)
      - ASCII key=value frames (for serial/TCP-connected oximeters)
    """

    device_type = DeviceType.SPO2
    supported_protocols = ["BLE-Custom-SpO2", "Custom-KV-SpO2-v1"]
    adapter_version = "1.0.0"

    def _validate_config(self) -> None:
        from mdil.base import AdapterConfigError

        mode = self.config.get("mode", "auto")
        if mode not in ("auto", "ble", "ascii"):
            raise AdapterConfigError(
                f"SpO2 adapter 'mode' must be 'auto', 'ble', or 'ascii'. Got: '{mode}'"
            )

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        mode = self.config.get("mode", "auto")

        if mode == "ble" or (mode == "auto" and isinstance(raw_frame, bytes)):
            return self._parse_ble(raw_frame)
        else:
            return self._parse_ascii(raw_frame)

    def _parse_ble(self, raw_frame: str | bytes) -> list[RawReading]:
        """
        Decode BLE binary SpO2 payload.
        Custom 4-byte format: [flags, spo2_pct, hr_lo, hr_hi]
        """
        if isinstance(raw_frame, str):
            raw_bytes = bytes.fromhex(raw_frame.replace(" ", ""))
        else:
            raw_bytes = raw_frame

        if len(raw_bytes) < 2:
            raise AdapterParseError(
                f"BLE SpO2 payload too short: {len(raw_bytes)} bytes (minimum 2).",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        flags = raw_bytes[0]
        spo2_pct = raw_bytes[1]

        # Validate SpO2 range
        if not (50 <= spo2_pct <= 100):
            raise AdapterParseError(
                f"BLE SpO2 value {spo2_pct}% is outside valid range [50, 100].",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        sensor_contact = bool(flags & _FLAG_SENSOR_CONTACT)
        quality = ReadingQuality.GOOD if sensor_contact else ReadingQuality.MARGINAL
        now = datetime.now(timezone.utc)

        readings: list[RawReading] = [
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.SPO2,
                value=spo2_pct,
                unit=Unit.PERCENT,
                raw_payload=raw_frame,
                quality=quality,
                metadata={"sensor_contact": sensor_contact},
            )
        ]

        # Parse heart rate if present
        hr_16bit = bool(flags & _FLAG_HR_16BIT)
        if hr_16bit and len(raw_bytes) >= 4:
            hr = struct.unpack_from("<H", raw_bytes, 2)[0]
        elif not hr_16bit and len(raw_bytes) >= 3:
            hr = raw_bytes[2]
        else:
            hr = None

        if hr is not None and 0 <= hr <= 300:
            readings.append(
                RawReading(
                    device_type=self.device_type,
                    device_id=self.device_id,
                    captured_at=now,
                    metric=MetricType.HEART_RATE,
                    value=hr,
                    unit=Unit.BPM,
                    raw_payload=raw_frame,
                    quality=quality,
                    metadata={"source": "spo2_ble_hr"},
                )
            )

        return readings

    def _parse_ascii(self, raw_frame: str | bytes) -> list[RawReading]:
        """Parse ASCII key=value SpO2 frame."""
        if isinstance(raw_frame, bytes):
            try:
                frame_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"SpO2 ASCII frame decode error: {exc}",
                    raw_frame=raw_frame,
                    device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            frame_str = raw_frame.strip()

        if not frame_str:
            return []

        pairs = {k.upper(): v for k, v in _KV_PATTERN.findall(frame_str)}

        if "SPO2" not in pairs:
            raise AdapterParseError(
                f"SpO2 ASCII frame missing 'SPO2' field. Frame: '{frame_str}'",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            spo2 = float(pairs["SPO2"])
        except ValueError:
            raise AdapterParseError(
                f"Invalid SPO2 value: '{pairs['SPO2']}'",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        sq_raw = pairs.get("SQ", "unknown").lower()
        quality = _QUALITY_MAP.get(sq_raw, ReadingQuality.UNKNOWN)
        now = datetime.now(timezone.utc)
        readings: list[RawReading] = [
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.SPO2,
                value=spo2,
                unit=Unit.PERCENT,
                raw_payload=frame_str,
                quality=quality,
                metadata={"perfusion_index": float(pairs["PI"]) if "PI" in pairs else None},
            )
        ]

        if "PR" in pairs:
            try:
                pr = float(pairs["PR"])
                readings.append(
                    RawReading(
                        device_type=self.device_type,
                        device_id=self.device_id,
                        captured_at=now,
                        metric=MetricType.HEART_RATE,
                        value=pr,
                        unit=Unit.BPM,
                        raw_payload=frame_str,
                        quality=quality,
                    )
                )
            except ValueError:
                pass

        return readings
