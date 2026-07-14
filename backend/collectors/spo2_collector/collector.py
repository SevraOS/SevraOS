"""
HELIOS OS + SEVRA AI
SpO2 Collector

Connects to a pulse oximeter via BLE or serial transport.
Supports both BLE binary payload and ASCII frames.

Config keys (from spo2_collector/config.yaml):
    device_id            : str   — unique device ID
    transport            : str   — "ble" | "serial"
    ble_address          : str   — BLE MAC address (ble only)
    service_uuid         : str   — GATT service UUID (ble only)
    characteristic_uuid  : str   — GATT characteristic UUID (ble only)
    port                 : str   — serial port (serial only)
    baud_rate            : int   — serial baud rate
    adapter_mode         : str   — "auto" | "ble" | "ascii"
"""

from __future__ import annotations

from typing import Any

from collectors.base.collector_base import BaseCollector
from mdil.adapters.spo2_adapter import SpO2Adapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport
from mdil.transports.ble_transport import BLETransport
from mdil.transports.serial_transport import SerialTransport


class SpO2Collector(BaseCollector):
    """
    Pulse Oximeter Collector.
    Supports BLE and serial transports.
    """

    collector_name = "spo2_collector"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(
            device_id=config["device_id"],
            device_type=DeviceType.SPO2,
            config=config,
            **kwargs,
        )
        self._transport_type: str = config.get("transport", "ble")

    def build_transport(self) -> BaseTransport:
        if self._transport_type == "ble":
            return BLETransport(
                device_id=self.device_id,
                config={
                    "ble_address": self.config["ble_address"],
                    "service_uuid": self.config["service_uuid"],
                    "characteristic_uuid": self.config["characteristic_uuid"],
                    "scan_timeout": self.config.get("scan_timeout", 10.0),
                    "disconnect_timeout": self.config.get("disconnect_timeout", 5.0),
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
        return SpO2Adapter(
            device_id=self.device_id,
            config={
                "mode": self.config.get("adapter_mode", "auto"),
                "ward": self.config.get("ward"),
                "bed": self.config.get("bed"),
                "facility_id": self.config.get("facility_id", "FACILITY-001"),
            },
        )
