"""
HELIOS OS + SEVRA AI
Infusion Pump Collector

Connects to an infusion pump via socket or serial transport.
Supports both binary (16-byte) and ASCII key=value frame formats.

Config keys (from infusion_collector/config.yaml):
    device_id    : str  — unique device ID
    transport    : str  — "socket" | "serial"
    host         : str  — TCP hostname (socket only)
    tcp_port     : int  — TCP port (socket only)
    port         : str  — serial port (serial only)
    baud_rate    : int  — serial baud rate
    adapter_mode : str  — "auto" | "binary" | "ascii"
    frame_size   : int  — fixed frame size in bytes (binary mode)
"""

from __future__ import annotations

from typing import Any

from collectors.base.collector_base import BaseCollector
from mdil.adapters.infusion_adapter import InfusionAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport
from mdil.transports.serial_transport import SerialTransport
from mdil.transports.socket_transport import SocketTransport


class InfusionCollector(BaseCollector):
    """
    Infusion Pump Collector.
    Supports socket and serial transports with binary or ASCII frames.
    """

    collector_name = "infusion_collector"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            device_id=config["device_id"],
            device_type=DeviceType.INFUSION_PUMP,
            config=config,
            **kwargs,
        )
        self._transport_type: str = config.get("transport", "serial")

    def build_transport(self) -> BaseTransport:
        adapter_mode = self.config.get("adapter_mode", "auto")
        # Binary mode: use fixed frame_size
        frame_size = self.config.get("frame_size") if adapter_mode == "binary" else None

        if self._transport_type == "socket":
            return SocketTransport(
                device_id=self.device_id,
                config={
                    "host": self.config["host"],
                    "port": self.config["tcp_port"],
                    "protocol": "raw",
                    "frame_size": frame_size,
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
                "baud_rate": self.config.get("baud_rate", 9600),
                "timeout": self.config.get("read_timeout", 2.0),
                "frame_size": frame_size,
                "frame_delimiter": self.config.get("frame_delimiter", "\r\n"),
            },
        )

    def build_adapter(self) -> DeviceAdapter:
        return InfusionAdapter(
            device_id=self.device_id,
            config={
                "mode": self.config.get("adapter_mode", "auto"),
                "ward": self.config.get("ward"),
                "bed": self.config.get("bed"),
                "facility_id": self.config.get("facility_id", "FACILITY-001"),
            },
        )
