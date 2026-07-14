"""
HELIOS OS + SEVRA AI
DeviceAdapter — Abstract Base Class

All device adapters inherit from DeviceAdapter.
An adapter's sole responsibility is to:
  1. Accept raw bytes or string from a Transport
  2. Parse it into one or more RawReadings
  3. Return the results (never push directly to streams)

Adapters are stateless — all device state lives in the Collector.
Adapters do NOT communicate with Redis.
Adapters do NOT perform validation.
Adapters raise AdapterParseError on unrecoverable parse failures.
"""

from __future__ import annotations

import abc
import time
from typing import Any, Sequence, Tuple, List, Optional

import structlog

from mdil.schema import DeviceType, RawReading

logger = structlog.get_logger(__name__)


# ── Adapter Exceptions ────────────────────────────────────────────────────────

class AdapterError(Exception):
    """Base for all adapter-level errors."""


class AdapterParseError(AdapterError):
    """
    Raised when a frame cannot be parsed into a RawReading.
    The Collector catches this and increments its parse_error counter.
    The raw_frame is included for DLQ routing.
    """

    def __init__(
        self,
        message: str,
        raw_frame: str | bytes,
        device_id: str,
        device_type: DeviceType,
    ) -> None:
        super().__init__(message)
        self.raw_frame = raw_frame
        self.device_id = device_id
        self.device_type = device_type


class AdapterConfigError(AdapterError):
    """Raised when adapter configuration is missing or invalid."""


# ── DeviceAdapter Abstract Base ───────────────────────────────────────────────

class DeviceAdapter(abc.ABC):
    """
    Abstract base for all HELIOS device adapters.

    One adapter class handles one device protocol variant.
    Adapters are registered in the AdapterRegistry and looked up
    by the Collector at runtime.

    Implementation contract:
      - parse() must be deterministic: same input → same output
      - parse() must not perform I/O
      - parse() must not mutate shared state
      - parse() must complete in < 10ms (99th percentile)
    """

    # ── Subclass must define these ────────────────────────────────────────────
    device_type: DeviceType
    """The device category this adapter handles."""

    supported_protocols: list[str] = []
    """Protocol identifiers this adapter can parse (e.g., ["HL7v2", "Custom"])."""

    adapter_version: str = "1.0.0"
    """Semantic version of the adapter implementation."""

    def __init__(self, device_id: str, config: dict[str, Any] | None = None) -> None:
        """
        Args:
            device_id: The registered device identifier.
            config: Optional adapter-specific configuration dict.
        """
        self.device_id = device_id
        self.config = config or {}
        self._parse_count: int = 0
        self._error_count: int = 0
        self._log = logger.bind(
            device_id=device_id,
            device_type=self.device_type,
            adapter=self.__class__.__name__,
        )
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Override to validate adapter-specific config fields.
        Raise AdapterConfigError if required config is missing.
        """

    @abc.abstractmethod
    def parse(self, raw_frame: str | bytes) -> Sequence[RawReading]:
        """
        Parse a raw device frame into one or more RawReadings.

        Args:
            raw_frame: Raw bytes or ASCII string from the transport layer.

        Returns:
            Sequence of RawReading objects (may be empty if frame is a heartbeat).

        Raises:
            AdapterParseError: if the frame is malformed or unparseable.
        """

    def parse_safe(self, raw_frame: str | bytes) -> Tuple[List[RawReading], Optional[AdapterParseError]]:
        """
        Safe wrapper around parse().
        Returns (readings, None) on success.
        Returns ([], error) on AdapterParseError without raising.
        Always safe to call — never raises.
        """
        start = time.perf_counter()
        try:
            readings = list(self.parse(raw_frame))
            self._parse_count += 1
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._log.debug(
                "adapter_parse_success",
                readings_count=len(readings),
                elapsed_ms=round(elapsed_ms, 2),
            )
            return readings, None
        except AdapterParseError as exc:
            self._error_count += 1
            self._log.warning(
                "adapter_parse_error",
                error=str(exc),
                raw_frame_preview=_preview(raw_frame),
            )
            return [], exc
        except Exception as exc:
            self._error_count += 1
            self._log.error(
                "adapter_unexpected_error",
                error=str(exc),
                exc_info=True,
            )
            parse_error = AdapterParseError(
                message=f"Unexpected error: {exc}",
                raw_frame=raw_frame,
                device_id=self.device_id,
                device_type=self.device_type,
            )
            return [], parse_error

    @property
    def stats(self) -> dict[str, int]:
        """Return parse/error counters for health monitoring."""
        return {
            "parse_count": self._parse_count,
            "error_count": self._error_count,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"device_id={self.device_id!r}, "
            f"device_type={self.device_type!r})"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _preview(raw_frame: str | bytes, max_len: int = 64) -> str:
    """Return a safe printable preview of the raw frame for logging."""
    if isinstance(raw_frame, bytes):
        preview = raw_frame[:max_len].hex()
    else:
        preview = str(raw_frame)[:max_len]
    return preview
