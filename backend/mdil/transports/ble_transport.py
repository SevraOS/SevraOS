"""
HELIOS OS + SEVRA AI
BLE Transport

Async Bluetooth Low Energy transport using the `bleak` library.
Used by: portable SpO2 sensors, wearable glucose monitors, BLE BP cuffs.

Config keys:
    ble_address (str): BLE device MAC address or UUID
    service_uuid (str): GATT service UUID to subscribe to
    characteristic_uuid (str): GATT characteristic UUID for notifications
    scan_timeout (float): BLE scan timeout in seconds (default 10.0)
    disconnect_timeout (float): Disconnect wait timeout (default 5.0)
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import structlog

from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError

logger = structlog.get_logger(__name__)


class BLETransport(BaseTransport):
    """
    Async BLE GATT notification transport.

    Subscribes to a BLE characteristic and yields notification payloads
    as byte frames. Each BLE notification is one frame.
    """

    transport_type = "ble"

    def __init__(self, device_id: str, config: dict) -> None:
        super().__init__(device_id, config)
        self._ble_address: str = config["ble_address"]
        self._service_uuid: str = config["service_uuid"]
        self._characteristic_uuid: str = config["characteristic_uuid"]
        self._scan_timeout: float = config.get("scan_timeout", 10.0)
        self._disconnect_timeout: float = config.get("disconnect_timeout", 5.0)
        self._client: Optional[object] = None
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=256)

    async def connect(self) -> None:
        try:
            from bleak import BleakClient  # type: ignore[import]

            self._client = BleakClient(
                self._ble_address,
                timeout=self._scan_timeout,
            )
            await self._client.connect()  # type: ignore[union-attr]

            if not self._client.is_connected:  # type: ignore[union-attr]
                raise TransportConnectionError(
                    f"BLE device {self._ble_address} refused connection.",
                    device_id=self.device_id,
                )

            await self._client.start_notify(  # type: ignore[union-attr]
                self._characteristic_uuid,
                self._on_notification,
            )

            self._connected = True
            self._log.info(
                "ble_connected",
                address=self._ble_address,
                characteristic=self._characteristic_uuid,
            )
        except ImportError:
            raise TransportConnectionError(
                "bleak library is not installed. Install with: pip install bleak",
                device_id=self.device_id,
            )
        except Exception as exc:
            self._connected = False
            raise TransportConnectionError(
                f"BLE connection to {self._ble_address} failed: {exc}",
                device_id=self.device_id,
            ) from exc

    def _on_notification(self, _sender: object, data: bytearray) -> None:
        """Called by bleak on BLE notification. Enqueues the payload."""
        try:
            self._frame_queue.put_nowait(bytes(data))
        except asyncio.QueueFull:
            self._log.warning("ble_frame_queue_full_dropping_frame")

    async def disconnect(self) -> None:
        self._connected = False
        if self._client is not None:
            try:
                await asyncio.wait_for(
                    self._client.disconnect(),  # type: ignore[union-attr]
                    timeout=self._disconnect_timeout,
                )
            except Exception:
                pass
            self._client = None
        self._log.info("ble_disconnected", address=self._ble_address)

    async def read_frames(self) -> AsyncIterator[bytes]:
        if not self._connected:
            raise TransportConnectionError("BLE not connected.", device_id=self.device_id)

        while self._connected:
            try:
                frame = await asyncio.wait_for(
                    self._frame_queue.get(),
                    timeout=5.0,
                )
                self._bytes_received += len(frame)
                self._frames_received += 1
                yield frame
            except asyncio.TimeoutError:
                # No notification in 5 seconds — check connection
                if self._client and not self._client.is_connected:  # type: ignore[union-attr]
                    self._connected = False
                    raise TransportReadError(
                        f"BLE device {self._ble_address} disconnected.",
                        device_id=self.device_id,
                    )
