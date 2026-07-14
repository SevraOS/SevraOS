"""
HELIOS OS + SEVRA AI
Infusion Pump Adapter

Binary payload format (16 bytes):
    Bytes 0-1:  Magic header (0xAA 0xBB)
    Bytes 2-3:  Sequence number (uint16 LE)
    Bytes 4-7:  Flow rate × 100 (uint32 LE) → mL/h
    Bytes 8-11: Volume delivered × 10 (uint32 LE) → mL
    Bytes 12-15: Volume remaining × 10 (uint32 LE) → mL

ASCII format:
    FLOW=125.50 VD=125.5 VR=374.5 DRUG=Morphine CONC=1.0 UNIT=mg/mL
"""

from __future__ import annotations

import re
import struct
from datetime import datetime, timezone
from typing import Sequence

import structlog

from mdil.base import DeviceAdapter, AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, RawReading, ReadingQuality, Unit

logger = structlog.get_logger(__name__)

_BINARY_MAGIC = b"\xAA\xBB"
_BINARY_FRAME_SIZE = 16
_KV_PATTERN = re.compile(r"(\w+)=([^\s]+)")


@AdapterRegistry.register
class InfusionAdapter(DeviceAdapter):
    """
    Infusion Pump Adapter.
    Supports binary (16-byte proprietary) and ASCII key=value frames.
    Auto-detects frame type from magic header.
    """

    device_type = DeviceType.INFUSION_PUMP
    supported_protocols = ["Binary-Infusion-v1", "Custom-KV-Infusion-v1"]
    adapter_version = "1.0.0"

    def _validate_config(self) -> None:
        from mdil.base import AdapterConfigError
        mode = self.config.get("mode", "auto")
        if mode not in ("auto", "binary", "ascii"):
            raise AdapterConfigError(
                f"Infusion adapter 'mode' must be 'auto', 'binary', or 'ascii'. Got: '{mode}'"
            )

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        mode = self.config.get("mode", "auto")
        if mode == "binary":
            return self._parse_binary(raw_frame)
        elif mode == "ascii":
            return self._parse_ascii(raw_frame)
        # Auto-detect
        if isinstance(raw_frame, bytes) and raw_frame[:2] == _BINARY_MAGIC:
            return self._parse_binary(raw_frame)
        return self._parse_ascii(raw_frame)

    def _parse_binary(self, raw_frame: str | bytes) -> list[RawReading]:
        if isinstance(raw_frame, str):
            try:
                raw_bytes = bytes.fromhex(raw_frame.replace(" ", ""))
            except ValueError as exc:
                raise AdapterParseError(
                    f"Infusion binary frame is not valid hex: {exc}",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            raw_bytes = raw_frame

        if len(raw_bytes) < _BINARY_FRAME_SIZE:
            raise AdapterParseError(
                f"Infusion binary frame too short: {len(raw_bytes)} bytes "
                f"(expected {_BINARY_FRAME_SIZE}).",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        if raw_bytes[:2] != _BINARY_MAGIC:
            raise AdapterParseError(
                f"Infusion binary invalid magic: {raw_bytes[:2].hex()} (expected AABB).",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            seq_num, flow_raw, vol_del_raw, vol_rem_raw = struct.unpack_from(
                "<HIII", raw_bytes, offset=2
            )
        except struct.error as exc:
            raise AdapterParseError(
                f"Infusion binary unpack failed: {exc}",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        flow_rate = flow_raw / 100.0
        vol_delivered = vol_del_raw / 10.0
        vol_remaining = vol_rem_raw / 10.0
        self._validate_ranges(flow_rate, vol_delivered, vol_remaining, raw_frame)

        now = datetime.now(timezone.utc)
        return [
            RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_FLOW_RATE,
                value=flow_rate, unit=Unit.ML_PER_HOUR, raw_payload=raw_frame,
                quality=ReadingQuality.GOOD, sequence_number=seq_num,
                metadata={"protocol": "binary"},
            ),
            RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_VOLUME_DELIVERED,
                value=vol_delivered, unit=Unit.ML, raw_payload=raw_frame,
                quality=ReadingQuality.GOOD, sequence_number=seq_num,
                metadata={"protocol": "binary"},
            ),
            RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_VOLUME_REMAINING,
                value=vol_remaining, unit=Unit.ML, raw_payload=raw_frame,
                quality=ReadingQuality.GOOD, sequence_number=seq_num,
                metadata={"protocol": "binary"},
            ),
        ]

    def _parse_ascii(self, raw_frame: str | bytes) -> list[RawReading]:
        if isinstance(raw_frame, bytes):
            try:
                frame_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"Infusion ASCII decode error: {exc}",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            frame_str = raw_frame.strip()

        if not frame_str:
            return []

        pairs = {k.upper(): v for k, v in _KV_PATTERN.findall(frame_str)}

        if "FLOW" not in pairs:
            raise AdapterParseError(
                f"Infusion ASCII frame missing 'FLOW'. Frame: '{frame_str}'",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            flow_rate = float(pairs["FLOW"])
        except ValueError as exc:
            raise AdapterParseError(
                f"Infusion FLOW non-numeric: '{pairs['FLOW']}'. {exc}",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )

        vol_delivered = self._opt_float(pairs, "VD")
        vol_remaining = self._opt_float(pairs, "VR")
        self._validate_ranges(flow_rate, vol_delivered, vol_remaining, raw_frame)

        now = datetime.now(timezone.utc)
        readings: list[RawReading] = [
            RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_FLOW_RATE,
                value=flow_rate, unit=Unit.ML_PER_HOUR, raw_payload=frame_str,
                quality=ReadingQuality.GOOD, metadata={"protocol": "ascii"},
            ),
        ]

        if vol_delivered is not None:
            readings.append(RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_VOLUME_DELIVERED,
                value=vol_delivered, unit=Unit.ML, raw_payload=frame_str,
                quality=ReadingQuality.GOOD, metadata={"protocol": "ascii"},
            ))

        if vol_remaining is not None:
            readings.append(RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_VOLUME_REMAINING,
                value=vol_remaining, unit=Unit.ML, raw_payload=frame_str,
                quality=ReadingQuality.GOOD, metadata={"protocol": "ascii"},
            ))

        if "DRUG" in pairs:
            readings.append(RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_DRUG_NAME,
                value=pairs["DRUG"], unit=Unit.UNITLESS, raw_payload=frame_str,
                quality=ReadingQuality.GOOD, metadata={"protocol": "ascii"},
            ))

        conc = self._opt_float(pairs, "CONC")
        if conc is not None:
            readings.append(RawReading(
                device_type=self.device_type, device_id=self.device_id,
                captured_at=now, metric=MetricType.INFUSION_CONCENTRATION,
                value=conc, unit=Unit.UNITLESS, raw_payload=frame_str,
                quality=ReadingQuality.GOOD,
                metadata={"protocol": "ascii", "conc_unit": pairs.get("UNIT", "mg/mL")},
            ))

        return readings

    def _opt_float(self, pairs: dict[str, str], key: str) -> float | None:
        if key not in pairs:
            return None
        try:
            return float(pairs[key])
        except ValueError:
            self._log.warning("infusion_non_numeric_field", key=key, value=pairs[key])
            return None

    def _validate_ranges(
        self,
        flow_rate: float,
        vol_delivered: float | None,
        vol_remaining: float | None,
        raw_frame: str | bytes,
    ) -> None:
        if not (0.0 <= flow_rate <= 9999.99):
            raise AdapterParseError(
                f"Infusion flow rate {flow_rate} mL/h outside range [0, 9999.99].",
                raw_frame=raw_frame, device_id=self.device_id,
                device_type=self.device_type,
            )
        for vol, name in [(vol_delivered, "VD"), (vol_remaining, "VR")]:
            if vol is not None and not (0.0 <= vol <= 99999.9):
                raise AdapterParseError(
                    f"Infusion {name}={vol} mL outside range [0, 99999.9].",
                    raw_frame=raw_frame, device_id=self.device_id,
                    device_type=self.device_type,
                )
