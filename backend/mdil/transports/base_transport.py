"""
HELIOS OS + SEVRA AI
Base Transport

Abstract base class for all HELIOS transport implementations.
All transports yield raw bytes frames to the Collector.
"""

from __future__ import annotations

import abc
from typing import Any, AsyncIterator, Dict

import structlog

logger = structlog.get_logger(__name__)


# ── Transport Exceptions ──────────────────────────────────────────────────────

class TransportError(Exception):
    """Base transport error."""
    def __init__(self, message: str, device_id: str) -> None:
        super().__init__(message)
        self.device_id = device_id


class TransportConnectionError(TransportError):
    """Raised when a transport cannot establish or maintain a connection."""


class TransportReadError(TransportError):
    """Raised when a transport read operation fails."""


class TransportConfigError(TransportError):
    """Raised when transport configuration is invalid."""


# ── Base Transport ────────────────────────────────────────────────────────────

class BaseTransport(abc.ABC):
    """
    Abstract base class for all transport implementations.

    Responsibility:
      - Manage the raw connection (open, close, reconnect)
      - Yield raw byte frames to the Collector
      - Track connection metrics

    The Collector drives the transport — it calls connect(), read_frames(),
    and disconnect() in order. The Collector handles reconnection logic.
    """

    transport_type: str = "base"

    def __init__(self, device_id: str, config: Dict[str, Any]) -> None:
        self.device_id = device_id
        self.config = config
        self._connected: bool = False
        self._bytes_received: int = 0
        self._frames_received: int = 0
        self._log = logger.bind(
            device_id=device_id,
            transport=self.transport_type,
        )

    @abc.abstractmethod
    async def connect(self) -> None:
        """
        Establish the connection.
        Raises TransportConnectionError on failure.
        """

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Close the connection gracefully. Never raises."""

    @abc.abstractmethod
    async def read_frames(self) -> AsyncIterator[bytes]:
        """
        Yield raw byte frames indefinitely until disconnected.
        Raises TransportReadError on read failures.
        """

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> dict[str, int]:
        return {
            "bytes_received": self._bytes_received,
            "frames_received": self._frames_received,
        }

    async def __aenter__(self) -> "BaseTransport":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()
