"""
HELIOS OS + SEVRA AI
BaseCollector — Abstract Collector Base Class

Every device collector inherits from BaseCollector.
Responsibilities:
  1. Open transport connection
  2. Read raw frames in an async loop
  3. Invoke the device adapter (parse frames → RawReadings)
  4. Buffer readings in a bounded asyncio.Queue
  5. Forward readings to the validation interface
  6. Reconnect on failure with exponential backoff
  7. Update CollectorHealth throughout lifecycle

Architecture contract:
  - One collector instance per physical device
  - Collectors do NOT communicate with each other
  - Collectors do NOT validate data (pass-through to ValidationInterface)
  - Collectors own the transport lifecycle
  - Reconnect strategy: exponential backoff with jitter
"""

from __future__ import annotations

import abc
import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Optional, Dict

import structlog

from collectors.base.health import CollectorHealth, DeviceStatus
from mdil.base import DeviceAdapter, AdapterParseError
from mdil.schema import RawReading
from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError

logger = structlog.get_logger(__name__)


class BaseCollector(abc.ABC):
    """
    Abstract base for all HELIOS device collectors.

    Subclasses must implement:
      - build_transport() → BaseTransport
      - build_adapter()   → DeviceAdapter

    Optionally override:
      - configure_device() — send init commands after connect
      - split_frames()     — custom frame splitting logic
    """

    # ── Subclass must define ──────────────────────────────────────────────────
    collector_name: str = "base_collector"

    def __init__(
        self,
        device_id: str,
        device_type: str,
        config: Dict[str, Any],
        validation_queue: Optional[asyncio.Queue[RawReading]] = None,
    ) -> None:
        """
        Args:
            device_id:         Unique device identifier.
            device_type:       DeviceType string (e.g. "ecg").
            config:            Device configuration dict (from YAML).
            validation_queue:  Output queue to the validation interface.
                               If None, readings are discarded (useful in tests).
        """
        self.device_id = device_id
        self.device_type = device_type
        self.config = config
        self._validation_queue = validation_queue or asyncio.Queue(maxsize=1000)
        self._frame_buffer: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=config.get("frame_buffer_size", 512)
        )
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self._running: bool = False
        self._stop_event: asyncio.Event = asyncio.Event()

        # Reconnect settings
        self._reconnect_base_delay: float = config.get("reconnect_base_delay", 1.0)
        self._reconnect_max_delay: float = config.get("reconnect_max_delay", 60.0)
        self._reconnect_factor: float = config.get("reconnect_factor", 2.0)
        self._max_reconnect_attempts: int = config.get("max_reconnect_attempts", 0)  # 0 = infinite

        # Health monitoring
        self.health = CollectorHealth(
            device_id=device_id,
            device_type=device_type,
        )

        self._log = logger.bind(
            collector=self.collector_name,
            device_id=device_id,
            device_type=device_type,
        )

    # ── Abstract Interface ────────────────────────────────────────────────────

    @abc.abstractmethod
    def build_transport(self) -> BaseTransport:
        """
        Build and return a configured transport for this device.
        Called fresh on every (re)connect attempt.
        """

    @abc.abstractmethod
    def build_adapter(self) -> DeviceAdapter:
        """
        Build and return a configured adapter for this device.
        Called once during collector startup.
        """

    # ── Optional hooks ────────────────────────────────────────────────────────

    async def configure_device(self, transport: BaseTransport) -> None:
        """
        Optional: Send device initialization commands after connection.
        E.g. set baud rate, request start streaming, etc.
        Default implementation does nothing.
        """

    def split_frames(self, raw_data: bytes) -> list[bytes]:
        """
        Optional: Split a raw chunk into individual frames.
        Default: each transport read is one frame (no splitting).
        Override for protocols that batch multiple frames per read.
        """
        return [raw_data]

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Start the collector loop.
        This coroutine runs until stop() is called or max retries exceeded.
        Designed to be run as an asyncio Task.
        """
        self._running = True
        self.health.started_at = datetime.now(timezone.utc)
        await self.health.set_status(DeviceStatus.INITIALIZING)
        self._log.info("collector_starting")

        adapter = self.build_adapter()
        attempt = 0

        while self._running and not self._stop_event.is_set():
            attempt += 1
            try:
                await self._connect_and_read(adapter)
                # If we exit cleanly (stop requested), break
                if self._stop_event.is_set():
                    break
            except Exception as exc:
                error_msg = str(exc)
                self._log.warning(
                    "collector_connection_lost",
                    attempt=attempt,
                    error=error_msg,
                )
                await self.health.mark_reconnecting(error_msg)

                # Check max attempts
                if self._max_reconnect_attempts > 0 and attempt >= self._max_reconnect_attempts:
                    await self.health.mark_failed(
                        f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded."
                    )
                    self._log.error("collector_max_retries_exceeded", attempts=attempt)
                    self._running = False
                    break

                # Exponential backoff with jitter
                delay = min(
                    self._reconnect_base_delay * (self._reconnect_factor ** (attempt - 1)),
                    self._reconnect_max_delay,
                )
                jitter = random.uniform(0, delay * 0.1)
                wait = delay + jitter
                self._log.info("collector_reconnect_backoff", wait_seconds=round(wait, 2))
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=wait,
                    )
                    break  # stop() was called during backoff
                except asyncio.TimeoutError:
                    pass  # timeout = time to retry

        await self.health.mark_stopped()
        self._log.info("collector_stopped", device_id=self.device_id)

    async def stop(self) -> None:
        """Signal the collector to stop gracefully."""
        self._running = False
        self._stop_event.set()
        self._log.info("collector_stop_requested")

    @property
    def is_running(self) -> bool:
        return self._running and not self._stop_event.is_set()

    # ── Internal Loop ─────────────────────────────────────────────────────────

    async def _connect_and_read(self, adapter: DeviceAdapter) -> None:
        """
        Connect transport, configure device, then run the read loop.
        Raises on transport/connection errors (caught by start() for backoff).
        """
        await self.health.set_status(DeviceStatus.CONNECTING)
        transport = self.build_transport()

        try:
            await transport.connect()
        except TransportConnectionError as exc:
            raise exc  # Propagate to backoff loop

        await self.health.mark_connected()
        self._log.info("collector_connected")

        try:
            await self.configure_device(transport)
        except Exception as exc:
            self._log.warning("collector_device_configure_error", error=str(exc))

        # Start concurrent producer (reads from transport) and consumer (processes frames)
        producer_task = asyncio.create_task(
            self._producer_loop(transport),
            name=f"producer_{self.device_id}",
        )
        consumer_task = asyncio.create_task(
            self._consumer_loop(adapter),
            name=f"consumer_{self.device_id}",
        )

        try:
            done, pending = await asyncio.wait(
                [producer_task, consumer_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc
        finally:
            for task in [producer_task, consumer_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
            await transport.disconnect()
            await self.health.update_stats(transport.stats, adapter.stats)

    async def _producer_loop(self, transport: BaseTransport) -> None:
        """
        Read frames from transport and push into the frame buffer.
        Stops when the stop_event is set or a TransportReadError occurs.
        """
        try:
            async for raw_chunk in transport.read_frames():
                if self._stop_event.is_set():
                    return
                for frame in self.split_frames(raw_chunk):
                    if not frame:
                        continue
                    try:
                        self._frame_buffer.put_nowait(frame)
                    except asyncio.QueueFull:
                        self._log.warning(
                            "collector_frame_buffer_full_dropping",
                            device_id=self.device_id,
                        )
        except TransportReadError as exc:
            self._log.warning("collector_transport_read_error", error=str(exc))
            raise

    async def _consumer_loop(self, adapter: DeviceAdapter) -> None:
        """
        Pull frames from the buffer, parse via adapter, forward RawReadings.
        Runs until stop_event is set.
        """
        while not self._stop_event.is_set():
            try:
                frame = await asyncio.wait_for(
                    self._frame_buffer.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            readings, parse_error = adapter.parse_safe(frame)

            if parse_error:
                await self.health.record_parse_error()
                self._log.warning(
                    "collector_parse_error",
                    error=str(parse_error),
                    frame_preview=frame[:64],
                )
                continue

            if readings:
                await self.health.record_frame(len(readings))
                for reading in readings:
                    await self._forward(reading)

    async def _forward(self, reading: RawReading) -> None:
        """
        Forward a RawReading to the validation queue.
        Drops on queue full with a warning (non-blocking).
        """
        try:
            self._validation_queue.put_nowait(reading)
        except asyncio.QueueFull:
            await self.health.record_forward_error()
            self._log.warning(
                "collector_validation_queue_full_dropping",
                reading_id=reading.reading_id,
                metric=reading.metric,
            )
