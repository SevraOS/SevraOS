"""
HELIOS OS + SEVRA AI
Validation Interface

Clean interface between the Collector layer and the Validation layer.

This module defines:
  - ValidationInterface: abstract base for all validation implementations
  - QueueValidationInterface: asyncio.Queue-based pass-through (default)
  - NullValidationInterface: drops all readings (useful in tests)

The actual validation logic is NOT implemented here.
It will be provided by Prompt 4 (Validation & Normalization).

Collectors forward RawReadings to ValidationInterface.forward().
The Validation layer consumes from its own queue or stream.

Contract:
  - forward() must never raise (wrap in try/except internally)
  - forward() must be non-blocking (async, bounded queue)
  - forward() is called for every RawReading from every collector
"""

from __future__ import annotations

import abc
import asyncio
from typing import Any

import structlog

from mdil.schema import RawReading

logger = structlog.get_logger(__name__)


class ValidationInterface(abc.ABC):
    """
    Abstract interface between Collectors and the Validation layer.

    Implemented by the Validation Service (Prompt 4).
    """

    @abc.abstractmethod
    async def forward(self, reading: RawReading) -> None:
        """
        Forward a RawReading for validation.

        Must never raise. Must be non-blocking.
        Implementation should use bounded queues.
        """

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the validation consumer loop."""

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the validation consumer loop gracefully."""


class QueueValidationInterface(ValidationInterface):
    """
    Default asyncio.Queue-based validation interface.

    Collectors push RawReadings into an asyncio.Queue.
    The Validation Service (Prompt 4) will replace this
    with a Redis Streams publisher.

    For now, readings are buffered in memory and can be
    consumed by calling drain().
    """

    def __init__(self, maxsize: int = 10_000) -> None:
        self._queue: asyncio.Queue[RawReading] = asyncio.Queue(maxsize=maxsize)
        self._running: bool = False
        self._dropped: int = 0
        self._received: int = 0
        self._log = logger.bind(component="QueueValidationInterface")

    async def forward(self, reading: RawReading) -> None:
        """Enqueue a RawReading. Drops if queue is full (non-blocking)."""
        try:
            self._queue.put_nowait(reading)
            self._received += 1
        except asyncio.QueueFull:
            self._dropped += 1
            self._log.warning(
                "validation_queue_full_dropping",
                reading_id=reading.reading_id,
                device_id=reading.device_id,
                metric=reading.metric,
            )

    async def start(self) -> None:
        self._running = True
        self._log.info("validation_interface_started")

    async def stop(self) -> None:
        self._running = False
        self._log.info("validation_interface_stopped")

    async def drain(self) -> list[RawReading]:
        """
        Drain all pending readings from the queue.
        Returns empty list if queue is empty.
        Used by tests and the future Validation Service.
        """
        readings: list[RawReading] = []
        while not self._queue.empty():
            try:
                readings.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return readings

    async def get_next(self, timeout: float = 5.0) -> RawReading | None:
        """
        Get the next reading with a timeout.
        Returns None on timeout.
        """
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "total_received": self._received,
            "total_dropped": self._dropped,
        }


class NullValidationInterface(ValidationInterface):
    """
    No-op validation interface that discards all readings.
    Use in unit tests where reading content is already validated.
    """

    async def forward(self, reading: RawReading) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
