"""
HELIOS OS + SEVRA AI
Serial Transport

Async RS-232/RS-485 serial port reader.
Used by: ECG monitors, Ventilators, older BP monitors.

Reads line-by-line or fixed-length frames from serial port.
On disconnect: applies exponential backoff and reconnects automatically.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import structlog

from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError

logger = structlog.get_logger(__name__)


class SerialTransport(BaseTransport):
    """
    Async serial port transport using pyserial-asyncio.

    Config keys:
        port (str): Serial port path, e.g., "/dev/ttyUSB0" or "COM3"
        baud_rate (int): Baud rate, default 9600
        bytesize (int): 5, 6, 7, or 8 (default 8)
        parity (str): 'N', 'E', 'O', 'M', 'S' (default 'N')
        stopbits (float): 1, 1.5, or 2 (default 1)
        timeout (float): Read timeout in seconds (default 2.0)
        frame_delimiter (str): Line delimiter in ASCII (default "\\r\\n")
        frame_size (int): Fixed frame size in bytes. If set, reads fixed frames.
    """

    transport_type = "serial"

    def __init__(self, device_id: str, config: dict) -> None:
        super().__init__(device_id, config)
        self._port: str = config["port"]
        self._baud_rate: int = config.get("baud_rate", 9600)
        self._bytesize: int = config.get("bytesize", 8)
        self._parity: str = config.get("parity", "N")
        self._stopbits: float = config.get("stopbits", 1)
        self._timeout: float = config.get("timeout", 2.0)
        self._frame_delimiter: bytes = config.get("frame_delimiter", "\r\n").encode()
        self._frame_size: Optional[int] = config.get("frame_size")
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._protocol: Optional[object] = None

    async def connect(self) -> None:
        """Open the serial port connection."""
        try:
            import serial_asyncio  # type: ignore[import]

            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=self._baud_rate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
            )
            self._connected = True
            self._log.info(
                "serial_connected",
                port=self._port,
                baud_rate=self._baud_rate,
            )
        except Exception as exc:
            self._connected = False
            raise TransportConnectionError(
                f"Failed to open serial port {self._port}: {exc}",
                device_id=self.device_id,
            ) from exc

    async def disconnect(self) -> None:
        """Close the serial port."""
        self._connected = False
        if self._writer and not self._writer.is_closing():
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None
        self._log.info("serial_disconnected", port=self._port)

    async def read_frames(self) -> AsyncIterator[bytes]:
        """
        Yield frames from the serial port.
        Fixed-size frame reading if frame_size is configured.
        Line-delimited reading otherwise.
        """
        if not self._reader or not self._connected:
            raise TransportConnectionError("Serial port not connected.", device_id=self.device_id)

        try:
            if self._frame_size:
                async for frame in self._read_fixed_frames():
                    yield frame
            else:
                async for frame in self._read_line_frames():
                    yield frame
        except asyncio.IncompleteReadError as exc:
            raise TransportReadError(
                f"Serial port {self._port} closed unexpectedly.",
                device_id=self.device_id,
            ) from exc
        except Exception as exc:
            raise TransportReadError(str(exc), device_id=self.device_id) from exc

    async def _read_line_frames(self) -> AsyncIterator[bytes]:
        """Read line-delimited frames."""
        assert self._reader is not None
        while self._connected:
            try:
                line = await asyncio.wait_for(
                    self._reader.readuntil(self._frame_delimiter),
                    timeout=self._timeout,
                )
                frame = line.rstrip(self._frame_delimiter)
                if frame:
                    self._bytes_received += len(line)
                    self._frames_received += 1
                    yield frame
            except asyncio.TimeoutError:
                # Timeout is normal — device may have no data
                continue

    async def _read_fixed_frames(self) -> AsyncIterator[bytes]:
        """Read fixed-size frames."""
        assert self._reader is not None and self._frame_size is not None
        while self._connected:
            try:
                frame = await asyncio.wait_for(
                    self._reader.readexactly(self._frame_size),
                    timeout=self._timeout,
                )
                self._bytes_received += self._frame_size
                self._frames_received += 1
                yield frame
            except asyncio.TimeoutError:
                continue
