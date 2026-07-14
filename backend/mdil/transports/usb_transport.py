"""
HELIOS OS + SEVRA AI
USB Transport

Async USB HID/bulk transfer transport.
Used by: USB glucometers, USB-connected infusion pumps, USB ECG leads.

Implements USB HID interrupt endpoint reading via pyusb (synchronous)
wrapped in an asyncio executor to keep the event loop non-blocking.

Config keys:
    vendor_id (int): USB vendor ID (hex, e.g., 0x04D9)
    product_id (int): USB product ID (hex, e.g., 0x1234)
    interface (int): USB interface number (default 0)
    endpoint (int): USB endpoint address (default 0x81 = IN endpoint 1)
    read_size (int): Bytes to read per transfer (default 64)
    read_timeout (int): USB read timeout in milliseconds (default 1000)
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import structlog

from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError

logger = structlog.get_logger(__name__)


class USBTransport(BaseTransport):
    """
    Async USB transport via pyusb.
    USB operations run in a thread pool executor to avoid blocking the event loop.
    """

    transport_type = "usb"

    def __init__(self, device_id: str, config: dict) -> None:
        super().__init__(device_id, config)
        self._vendor_id: int = config["vendor_id"]
        self._product_id: int = config["product_id"]
        self._interface: int = config.get("interface", 0)
        self._endpoint: int = config.get("endpoint", 0x81)
        self._read_size: int = config.get("read_size", 64)
        self._read_timeout: int = config.get("read_timeout", 1000)  # ms
        self._device: object | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> None:
        try:
            import usb.core  # type: ignore[import]
            import usb.util  # type: ignore[import]

            self._loop = asyncio.get_event_loop()
            dev = await self._loop.run_in_executor(
                None,
                lambda: usb.core.find(
                    idVendor=self._vendor_id,
                    idProduct=self._product_id,
                ),
            )

            if dev is None:
                raise TransportConnectionError(
                    f"USB device {self._vendor_id:#06x}:{self._product_id:#06x} not found.",
                    device_id=self.device_id,
                )

            # Detach kernel driver if active
            await self._loop.run_in_executor(None, self._setup_device, dev)
            self._device = dev
            self._connected = True
            self._log.info(
                "usb_connected",
                vendor_id=f"{self._vendor_id:#06x}",
                product_id=f"{self._product_id:#06x}",
            )
        except ImportError:
            raise TransportConnectionError(
                "pyusb is not installed. Install with: pip install pyusb",
                device_id=self.device_id,
            )
        except TransportConnectionError:
            raise
        except Exception as exc:
            self._connected = False
            raise TransportConnectionError(str(exc), device_id=self.device_id) from exc

    def _setup_device(self, dev: object) -> None:
        """Configure USB device (blocking — runs in executor)."""
        import usb.util  # type: ignore[import]

        if dev.is_kernel_driver_active(self._interface):  # type: ignore[union-attr]
            dev.detach_kernel_driver(self._interface)  # type: ignore[union-attr]
        dev.set_configuration()  # type: ignore[union-attr]
        usb.util.claim_interface(dev, self._interface)

    async def disconnect(self) -> None:
        self._connected = False
        if self._device and self._loop:
            try:
                import usb.util  # type: ignore[import]

                await self._loop.run_in_executor(
                    None,
                    lambda: usb.util.release_interface(self._device, self._interface),  # type: ignore[arg-type]
                )
            except Exception:
                pass
        self._device = None
        self._log.info("usb_disconnected")

    async def read_frames(self) -> AsyncIterator[bytes]:
        if not self._device or not self._connected or not self._loop:
            raise TransportConnectionError("USB not connected.", device_id=self.device_id)

        while self._connected:
            try:
                data = await self._loop.run_in_executor(
                    None,
                    lambda: self._device.read(  # type: ignore[union-attr]
                        self._endpoint,
                        self._read_size,
                        timeout=self._read_timeout,
                    ),
                )
                frame = bytes(data)
                if frame:
                    self._bytes_received += len(frame)
                    self._frames_received += 1
                    yield frame
            except Exception as exc:
                err_str = str(exc).lower()
                if "timeout" in err_str or "timed out" in err_str:
                    continue  # USB read timeout is normal
                raise TransportReadError(str(exc), device_id=self.device_id) from exc
