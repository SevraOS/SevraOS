"""
HELIOS OS + SEVRA AI
ECG Adapter

Parses ECG monitor frames into RawReadings.

Supported frame format (custom ASCII protocol):
    DAT|<heart_rate>|<amplitude_mV>|<lead>
    Example: DAT|72|0.84|II

Waveform batch format (multiple samples):
    WFM|<lead>|<sample_rate>|<s1>,<s2>,<s3>,...
    Example: WFM|II|500|0.12,0.14,0.95,1.02,0.87

Status frames (no reading produced):
    STA|OK
    STA|LEADOFF
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from mdil.base import DeviceAdapter, AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, RawReading, ReadingQuality, Unit


@AdapterRegistry.register
class ECGAdapter(DeviceAdapter):
    """
    ECG Monitor Adapter.

    Parses proprietary ASCII ECG frames into RawReadings.
    Supports scalar heart rate, waveform batches, and lead amplitude readings.
    """

    device_type = DeviceType.ECG
    supported_protocols = ["Custom-ASCII-ECG-v1"]
    adapter_version = "1.0.0"

    # Valid ECG leads
    _VALID_LEADS = {"I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"}
    _HEARTBEAT_STATUSES = {"OK", "CONNECTED", "ALIVE"}

    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        """
        Parse an ECG ASCII frame.

        Returns:
            List of RawReading objects.
            Empty list for heartbeat/status frames.

        Raises:
            AdapterParseError: if the frame is malformed.
        """
        if isinstance(raw_frame, bytes):
            try:
                frame_str = raw_frame.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise AdapterParseError(
                    f"ECG frame is not valid ASCII: {exc}",
                    raw_frame=raw_frame,
                    device_id=self.device_id,
                    device_type=self.device_type,
                )
        else:
            frame_str = raw_frame.strip()

        if not frame_str:
            return []

        parts = frame_str.split("|")
        frame_type = parts[0].upper()

        if frame_type == "DAT":
            return self._parse_dat_frame(parts, frame_str)
        elif frame_type == "WFM":
            return self._parse_wfm_frame(parts, frame_str)
        elif frame_type == "STA":
            return self._parse_status_frame(parts)
        else:
            raise AdapterParseError(
                f"Unknown ECG frame type: '{frame_type}'. Expected DAT|WFM|STA.",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )

    def _parse_dat_frame(self, parts: list[str], raw: str) -> list[RawReading]:
        """
        Parse DAT frame: DAT|<heart_rate>|<amplitude_mV>|<lead>

        Returns two RawReadings: heart_rate + ecg amplitude for the lead.
        """
        if len(parts) < 4:
            raise AdapterParseError(
                f"DAT frame malformed — expected 4 fields, got {len(parts)}: {raw}",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            heart_rate = float(parts[1])
        except ValueError:
            raise AdapterParseError(
                f"Invalid heart_rate value: '{parts[1]}'",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            amplitude_mv = float(parts[2])
        except ValueError:
            raise AdapterParseError(
                f"Invalid amplitude value: '{parts[2]}'",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        lead = parts[3].strip()
        if lead not in self._VALID_LEADS:
            raise AdapterParseError(
                f"Invalid ECG lead: '{lead}'. Valid: {self._VALID_LEADS}",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        now = datetime.now(timezone.utc)
        readings = []

        # Heart Rate reading
        readings.append(
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=MetricType.HEART_RATE,
                value=heart_rate,
                unit=Unit.BPM,
                raw_payload=raw,
                quality=ReadingQuality.GOOD,
                metadata={"lead": lead},
            )
        )

        # ECG amplitude for the lead
        lead_metric_map = {
            "I": MetricType.ECG_LEAD_I,
            "II": MetricType.ECG_LEAD_II,
            "III": MetricType.ECG_LEAD_III,
        }
        lead_metric = lead_metric_map.get(lead, MetricType.ECG_WAVEFORM)
        readings.append(
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=now,
                metric=lead_metric,
                value=amplitude_mv,
                unit=Unit.MV,
                raw_payload=raw,
                quality=ReadingQuality.GOOD,
                metadata={"lead": lead},
            )
        )

        return readings

    def _parse_wfm_frame(self, parts: list[str], raw: str) -> list[RawReading]:
        """
        Parse WFM (waveform batch) frame: WFM|<lead>|<sample_rate>|<s1>,<s2>,...
        Returns a single RawReading with value as list[float] (waveform samples).
        """
        if len(parts) < 4:
            raise AdapterParseError(
                f"WFM frame malformed — expected 4 fields, got {len(parts)}",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        lead = parts[1].strip()
        try:
            sample_rate = float(parts[2])
        except ValueError:
            raise AdapterParseError(
                f"Invalid sample_rate in WFM: '{parts[2]}'",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        try:
            samples = [float(s) for s in parts[3].split(",") if s.strip()]
        except ValueError as exc:
            raise AdapterParseError(
                f"Invalid sample values in WFM: {exc}",
                raw_frame=raw,
                device_id=self.device_id,
                device_type=self.device_type,
            )

        if not samples:
            return []

        return [
            RawReading(
                device_type=self.device_type,
                device_id=self.device_id,
                captured_at=datetime.now(timezone.utc),
                metric=MetricType.ECG_WAVEFORM,
                value=samples,
                unit=Unit.MV,
                raw_payload=raw,
                quality=ReadingQuality.GOOD,
                sampling_rate_hz=sample_rate,
                metadata={"lead": lead, "sample_count": len(samples)},
            )
        ]

    def _parse_status_frame(self, parts: list[str]) -> list[RawReading]:
        """STA frames are heartbeats or alerts — no reading produced."""
        if len(parts) >= 2:
            status = parts[1].strip().upper()
            if status not in self._HEARTBEAT_STATUSES:
                self._log.warning("ecg_device_status_non_ok", status=status)
        return []
