"""
HELIOS OS + SEVRA AI
Collector Health Monitor

Tracks per-collector device status, connection state, reading timestamps,
reconnect counts, and failure counts. Thread-safe via asyncio.Lock.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DeviceStatus(str, Enum):
    """Lifecycle status of a device collector."""
    INITIALIZING = "initializing"   # Collector created, not yet started
    CONNECTING = "connecting"       # Attempting transport connection
    CONNECTED = "connected"         # Actively reading data
    RECONNECTING = "reconnecting"   # Lost connection, backing off
    DEGRADED = "degraded"           # Connected but high error rate
    STOPPED = "stopped"             # Gracefully shut down
    FAILED = "failed"               # Permanently failed (max retries exceeded)


@dataclass
class CollectorHealth:
    """
    Health state for a single device collector.

    Instantiated by BaseCollector and updated throughout lifecycle.
    Read by the Supervisor and health API endpoints.
    """

    device_id: str
    device_type: str
    status: DeviceStatus = DeviceStatus.INITIALIZING

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at: datetime | None = None
    last_connected_at: datetime | None = None
    last_reading_at: datetime | None = None
    last_error_at: datetime | None = None

    # ── Counters ──────────────────────────────────────────────────────────────
    total_frames_received: int = 0
    total_readings_produced: int = 0
    total_parse_errors: int = 0
    total_forward_errors: int = 0
    reconnect_count: int = 0
    failure_count: int = 0

    # ── Current connection metadata ───────────────────────────────────────────
    last_error_message: str | None = None
    transport_stats: dict[str, Any] = field(default_factory=dict)
    adapter_stats: dict[str, Any] = field(default_factory=dict)

    # ── Internal lock ─────────────────────────────────────────────────────────
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)

    async def set_status(self, status: DeviceStatus) -> None:
        async with self._lock:
            self.status = status

    async def mark_connected(self) -> None:
        async with self._lock:
            self.status = DeviceStatus.CONNECTED
            self.last_connected_at = datetime.now(timezone.utc)

    async def mark_reconnecting(self, error: str) -> None:
        async with self._lock:
            self.status = DeviceStatus.RECONNECTING
            self.reconnect_count += 1
            self.failure_count += 1
            self.last_error_message = error
            self.last_error_at = datetime.now(timezone.utc)

    async def mark_failed(self, error: str) -> None:
        async with self._lock:
            self.status = DeviceStatus.FAILED
            self.last_error_message = error
            self.last_error_at = datetime.now(timezone.utc)

    async def mark_stopped(self) -> None:
        async with self._lock:
            self.status = DeviceStatus.STOPPED

    async def record_frame(self, readings_count: int) -> None:
        async with self._lock:
            self.total_frames_received += 1
            self.total_readings_produced += readings_count
            self.last_reading_at = datetime.now(timezone.utc)
            # Auto-recover from degraded if readings are flowing
            if self.status == DeviceStatus.DEGRADED:
                self.status = DeviceStatus.CONNECTED

    async def record_parse_error(self) -> None:
        async with self._lock:
            self.total_parse_errors += 1
            self.last_error_at = datetime.now(timezone.utc)
            # Mark degraded if error rate is high
            if self.status == DeviceStatus.CONNECTED:
                error_rate = self._error_rate()
                if error_rate > 0.20:  # >20% parse error rate
                    self.status = DeviceStatus.DEGRADED

    async def record_forward_error(self) -> None:
        async with self._lock:
            self.total_forward_errors += 1
            self.last_error_at = datetime.now(timezone.utc)

    async def update_stats(
        self,
        transport_stats: dict[str, Any],
        adapter_stats: dict[str, Any],
    ) -> None:
        async with self._lock:
            self.transport_stats = transport_stats
            self.adapter_stats = adapter_stats

    def _error_rate(self) -> float:
        total = self.total_frames_received
        if total == 0:
            return 0.0
        return self.total_parse_errors / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_connected_at": (
                self.last_connected_at.isoformat() if self.last_connected_at else None
            ),
            "last_reading_at": (
                self.last_reading_at.isoformat() if self.last_reading_at else None
            ),
            "last_error_at": (
                self.last_error_at.isoformat() if self.last_error_at else None
            ),
            "counters": {
                "frames_received": self.total_frames_received,
                "readings_produced": self.total_readings_produced,
                "parse_errors": self.total_parse_errors,
                "forward_errors": self.total_forward_errors,
                "reconnect_count": self.reconnect_count,
                "failure_count": self.failure_count,
            },
            "last_error_message": self.last_error_message,
            "transport_stats": self.transport_stats,
            "adapter_stats": self.adapter_stats,
        }

    def __repr__(self) -> str:
        return (
            f"CollectorHealth("
            f"device_id={self.device_id!r}, "
            f"status={self.status!r}, "
            f"frames={self.total_frames_received}, "
            f"errors={self.total_parse_errors})"
        )
