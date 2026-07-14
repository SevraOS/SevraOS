"""
HELIOS OS + SEVRA AI
Socket Transport

Async TCP socket transport for network-connected devices.
Used by: HL7v2-over-MLLP, DICOM modalities, network monitors.

Protocol support:
  - Raw TCP (line-delimited)
  - MLLP (Minimum Lower Layer Protocol) for HL7v2
  - Fixed-size frames

Config keys:
    host (str): Device hostname or IP
    port (int): TCP port
    protocol (str): "raw" | "mllp" (default "raw")
    frame_delimiter (str): Line delimiter for raw mode (default "\\r\\n")
    frame_size (int): Fixed frame size for binary protocols
    connect_timeout (float): Connection timeout in seconds (default 10.0)
    read_timeout (float): Read timeout (default 5.0)
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError

# MLLP framing constants (HL7v2)
MLLP_START_BLOCK = b"\x0b"
MLLP_END_BLOCK = b"\x1c"
MLLP_CARRIAGE_RETURN = b"\x0d"


class SocketTransport(BaseTransport):
    """Async TCP socket transport. Supports raw and MLLP protocols."""

    transport_type = "socket"

    def __init__(self, device_id: str, config: dict) -> None:
        super().__init__(device_id, config)
        self._host: str = config["host"]
        self._port: int = config["port"]
        self._protocol: str = config.get("protocol", "raw")
        self._frame_delimiter: bytes = config.get("frame_delimiter", "\r\n").encode()
        self._frame_size: int | None = config.get("frame_size")
        self._connect_timeout: float = config.get("connect_timeout", 10.0)
        self._read_timeout: float = config.get("read_timeout", 5.0)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._connect_timeout,
            )
            self._connected = True
            self._log.info("socket_connected", host=self._host, port=self._port)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as exc:
            self._connected = False
            raise TransportConnectionError(
                f"Cannot connect to {self._host}:{self._port} — {exc}",
                device_id=self.device_id,
            ) from exc

    async def disconnect(self) -> None:
        self._connected = False
        if self._writer and not self._writer.is_closing():
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None
        self._log.info("socket_disconnected", host=self._host, port=self._port)

    async def read_frames(self) -> AsyncIterator[bytes]:
        if not self._reader or not self._connected:
            raise TransportConnectionError("Socket not connected.", device_id=self.device_id)

        try:
            if self._protocol == "mllp":
                async for frame in self._read_mllp_frames():
                    yield frame
            elif self._frame_size:
                async for frame in self._read_fixed_frames():
                    yield frame
            else:
                async for frame in self._read_line_frames():
                    yield frame
        except (asyncio.IncompleteReadError, ConnectionResetError) as exc:
            raise TransportReadError(
                f"Socket {self._host}:{self._port} closed unexpectedly.",
                device_id=self.device_id,
            ) from exc

    async def _read_line_frames(self) -> AsyncIterator[bytes]:
        assert self._reader is not None
        while self._connected:
            try:
                line = await asyncio.wait_for(
                    self._reader.readuntil(self._frame_delimiter),
                    timeout=self._read_timeout,
                )
                frame = line.rstrip(self._frame_delimiter)
                if frame:
                    self._bytes_received += len(line)
                    self._frames_received += 1
                    yield frame
            except asyncio.TimeoutError:
                continue

    async def _read_fixed_frames(self) -> AsyncIterator[bytes]:
        assert self._reader is not None and self._frame_size is not None
        while self._connected:
            try:
                frame = await asyncio.wait_for(
                    self._reader.readexactly(self._frame_size),
                    timeout=self._read_timeout,
                )
                self._bytes_received += self._frame_size
                self._frames_received += 1
                yield frame
            except asyncio.TimeoutError:
                continue

    async def _read_mllp_frames(self) -> AsyncIterator[bytes]:
        """
        MLLP (Minimum Lower Layer Protocol) frame reader.
        Frame format: <VT> {HL7 message} <FS><CR>
        VT = 0x0B, FS = 0x1C, CR = 0x0D
        """
        assert self._reader is not None
        while self._connected:
            try:
                # Wait for start block (VT = 0x0B)
                start = await asyncio.wait_for(
                    self._reader.readuntil(MLLP_START_BLOCK),
                    timeout=self._read_timeout,
                )

                # Read until end block (FS = 0x1C)
                body = await asyncio.wait_for(
                    self._reader.readuntil(MLLP_END_BLOCK),
                    timeout=self._read_timeout,
                )
                # Strip the end block and trailing CR
                frame = body[:-1]  # Remove FS
                # Read and discard the trailing CR
                await self._reader.read(1)

                if frame:
                    self._bytes_received += len(frame)
                    self._frames_received += 1
                    yield frame

            except asyncio.TimeoutError:
                continue
