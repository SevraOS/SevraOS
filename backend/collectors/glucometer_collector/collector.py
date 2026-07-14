"""
HELIOS OS + SEVRA AI
Glucometer Collector

Connects to a glucometer via USB or serial transport.
Reads ASCII key=value glucose frames.

Config keys (from glucometer_collector/config.yaml):
    device_id   : str  — unique device ID
    transport   : str  — "usb" | "serial"
    vendor_id   : int  — USB vendor ID (usb only)
    product_id  : int  — USB product ID (usb only)
    port        : str  — serial port (serial only)
    baud_rate   : int  — serial baud rate
"""

from __future__ import annotations

from typing import Any

from collectors.base.collector_base import BaseCollector
from mdil.adapters.glucometer_adapter import GlucometerAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport
from mdil.transports.serial_transport import SerialTransport
from mdil.transports.usb_transport import USBTransport


class GlucometerCollector(BaseCollector):
    """
    Glucometer Collector.
    Supports USB (HID) and serial transports.
    """

    collector_name = "glucometer_collector"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            device_id=config["device_id"],
            device_type=DeviceType.GLUCOMETER,
            config=config,
            **kwargs,
        )
        self._transport_type: str = config.get("transport", "usb")

    def build_transport(self) -> BaseTransport:
        if self._transport_type == "usb":
            return USBTransport(
                device_id=self.device_id,
                config={
                    "vendor_id": self.config["vendor_id"],
                    "product_id": self.config["product_id"],
                    "interface": self.config.get("interface", 0),
                    "endpoint": self.config.get("endpoint", 0x81),
                    "read_size": self.config.get("read_size", 64),
                    "read_timeout": self.config.get("read_timeout_ms", 1000),
                },
            )
        # Serial fallback
        return SerialTransport(
            device_id=self.device_id,
            config={
                "port": self.config["port"],
                "baud_rate": self.config.get("baud_rate", 9600),
                "timeout": self.config.get("read_timeout", 2.0),
                "frame_delimiter": self.config.get("frame_delimiter", "\r\n"),
            },
        )

    def build_adapter(self) -> DeviceAdapter:
        return GlucometerAdapter(
            device_id=self.device_id,
            config={
                "ward": self.config.get("ward"),
                "bed": self.config.get("bed"),
                "facility_id": self.config.get("facility_id", "FACILITY-001"),
            },
        )
