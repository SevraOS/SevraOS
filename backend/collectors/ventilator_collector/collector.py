"""
HELIOS OS + SEVRA AI
Ventilator Collector

Connects to a mechanical ventilator via socket (MLLP/HL7) or serial transport.
Parses HL7 v2.x ORU^R01 messages into respiratory metrics RawReadings.

Config keys (from ventilator_collector/config.yaml):
    device_id       : str  — unique device ID
    transport       : str  — "socket" | "serial"
    host            : str  — TCP hostname (socket only)
    tcp_port        : int  — TCP port (socket only)
    protocol        : str  — "mllp" | "raw" (socket only, default: mllp)
    port            : str  — serial port (serial only)
    baud_rate       : int  — serial baud rate (serial only)
"""

from __future__ import annotations

from typing import Any

from collectors.base.collector_base import BaseCollector
from mdil.adapters.ventilator_adapter import VentilatorAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport
from mdil.transports.serial_transport import SerialTransport
from mdil.transports.socket_transport import SocketTransport


class VentilatorCollector(BaseCollector):
    """
    Mechanical Ventilator Collector.
    Supports MLLP/socket (primary) and serial transports.
    """

    collector_name = "ventilator_collector"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            device_id=config["device_id"],
            device_type=DeviceType.VENTILATOR,
            config=config,
            **kwargs,
        )
        self._transport_type: str = config.get("transport", "socket")

    def build_transport(self) -> BaseTransport:
        if self._transport_type == "socket":
            return SocketTransport(
                device_id=self.device_id,
                config={
                    "host": self.config["host"],
                    "port": self.config["tcp_port"],
                    "protocol": self.config.get("protocol", "mllp"),
                    "connect_timeout": self.config.get("connect_timeout", 10.0),
                    "read_timeout": self.config.get("read_timeout", 5.0),
                },
            )
        # Serial fallback
        return SerialTransport(
            device_id=self.device_id,
            config={
                "port": self.config["port"],
                "baud_rate": self.config.get("baud_rate", 9600),
                "timeout": self.config.get("read_timeout", 2.0),
                "frame_delimiter": "\r",  # HL7 segment terminator
            },
        )

    def build_adapter(self) -> DeviceAdapter:
        return VentilatorAdapter(
            device_id=self.device_id,
            config={
                "ward": self.config.get("ward"),
                "bed": self.config.get("bed"),
                "facility_id": self.config.get("facility_id", "FACILITY-001"),
            },
        )
