"""
HELIOS OS + SEVRA AI
Simulator Transport

In-memory transport that feeds simulator-generated frames directly
into the Collector pipeline without any physical device.

Design:
  - SimulatorTransport wraps an asyncio.Queue[bytes]
  - The caller (simulator) pushes frames into push_frame()
  - The Collector reads frames via read_frames() iterator
  - Zero network/serial dependencies — pure Python/asyncio

Usage:
    transport = SimulatorTransport(device_id="SIM-ECG-001")
    await transport.connect()
    await transport.push_frame(b"DAT|72|0.84|II")
    async for frame in transport.read_frames():
        print(frame)  # b"DAT|72|0.84|II"
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import structlog

from mdil.transports.base_transport import BaseTransport, TransportConnectionError

logger = structlog.get_logger(__name__)


class SimulatorTransport(BaseTransport):
    """
    In-memory simulator transport.

    Replaces any physical transport in a Collector for testing
    and integration validation without real hardware.
    """

    transport_type = "simulator"

    def __init__(
        self,
        device_id: str,
        config: Optional[dict] = None,
        queue_maxsize: int = 1024,
    ) -> None:
        super().__init__(device_id, config or {})
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=queue_maxsize)
        self._drain_timeout: float = 1.0

    async def connect(self) -> None:
        """Simulator connect is always instant."""
        self._connected = True
        self._log.info("simulator_transport_connected", device_id=self.device_id)

    async def disconnect(self) -> None:
        """Signal the read loop to stop by enqueuing a sentinel."""
        self._connected = False
        try:
            self._queue.put_nowait(None)  # Sentinel
        except asyncio.QueueFull:
            pass
        self._log.info("simulator_transport_disconnected", device_id=self.device_id)

    async def push_frame(self, frame: bytes) -> None:
        """
        Push a simulated frame into the transport.
        Called by the simulator — not by the Collector.
        Blocks if the queue is full.
        """
        await self._queue.put(frame)
        self._bytes_received += len(frame)
        self._frames_received += 1

    def push_frame_nowait(self, frame: bytes) -> None:
        """
        Non-blocking frame push.
        Drops the frame if queue is full (logs warning).
        """
        try:
            self._queue.put_nowait(frame)
            self._bytes_received += len(frame)
            self._frames_received += 1
        except asyncio.QueueFull:
            self._log.warning("simulator_queue_full_dropping", device_id=self.device_id)

    async def read_frames(self) -> AsyncIterator[bytes]:
        """
        Yield frames from the simulator queue.
        Returns when None sentinel is received (disconnect).
        """
        if not self._connected:
            raise TransportConnectionError(
                "SimulatorTransport not connected.", device_id=self.device_id
            )
        while self._connected:
            frame = await self._queue.get()
            if frame is None:  # Sentinel — stop iteration
                return
            yield frame
