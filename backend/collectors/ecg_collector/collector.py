"""
HELIOS OS + SEVRA AI
ECG Collector

Connects to an ECG monitor via serial or socket transport.
Reads ASCII frames (DAT|, WFM|, STA|) and forwards RawReadings.

Config keys (from ecg_collector/config.yaml):
    device_id        : str   — unique device ID
    transport        : str   — "serial" | "socket"
    port             : str   — serial port or host:port
    baud_rate        : int   — baud rate (serial only)
    host             : str   — hostname (socket only)
    tcp_port         : int   — TCP port (socket only)
    frame_buffer_size: int   — async frame buffer max size
    reconnect_*      : float — backoff settings
"""

from __future__ import annotations

from typing import Any

from collectors.base.collector_base import BaseCollector
from mdil.adapters.ecg_adapter import ECGAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport
from mdil.transports.serial_transport import SerialTransport
from mdil.transports.socket_transport import SocketTransport


class ECGCollector(BaseCollector):
    """
    ECG Monitor Collector.

    Supports serial and socket transports.
    Frames are line-delimited ASCII (default \\r\\n).
    """

    collector_name = "ecg_collector"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            device_id=config["device_id"],
            device_type=DeviceType.ECG,
            config=config,
            **kwargs,
        )
        self._transport_type: str = config.get("transport", "serial")

    def build_transport(self) -> BaseTransport:
        if self._transport_type == "socket":
            return SocketTransport(
                device_id=self.device_id,
                config={
                    "host": self.config["host"],
                    "port": self.config["tcp_port"],
                    "protocol": "raw",
                    "frame_delimiter": self.config.get("frame_delimiter", "\r\n"),
                    "connect_timeout": self.config.get("connect_timeout", 10.0),
                    "read_timeout": self.config.get("read_timeout", 5.0),
                },
            )
        # Default: serial
        return SerialTransport(
            device_id=self.device_id,
            config={
                "port": self.config["port"],
                "baud_rate": self.config.get("baud_rate", 115200),
                "bytesize": self.config.get("bytesize", 8),
                "parity": self.config.get("parity", "N"),
                "stopbits": self.config.get("stopbits", 1),
                "timeout": self.config.get("read_timeout", 2.0),
                "frame_delimiter": self.config.get("frame_delimiter", "\r\n"),
            },
        )

    def build_adapter(self) -> DeviceAdapter:
        return ECGAdapter(
            device_id=self.device_id,
            config={
                "ward": self.config.get("ward"),
                "bed": self.config.get("bed"),
                "facility_id": self.config.get("facility_id", "FACILITY-001"),
            },
        )
