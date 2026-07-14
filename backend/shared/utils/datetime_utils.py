"""
HELIOS OS + SEVRA AI
DateTime Utilities

Timezone-aware datetime helpers.
All timestamps in the platform use UTC ISO-8601.
Contract: Architecture Section C3.3 — all timestamps must be UTC ISO-8601.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> int:
    """Return the current UTC time as a Unix timestamp (integer seconds)."""
    return int(utc_now().timestamp())


def utc_from_timestamp(ts: float) -> datetime:
    """Convert a Unix timestamp (float) to a UTC-aware datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def to_iso8601(dt: datetime) -> str:
    """
    Convert a datetime to UTC ISO-8601 string.
    Always includes timezone offset (+00:00).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def from_iso8601(dt_str: str) -> datetime:
    """
    Parse an ISO-8601 datetime string to a UTC-aware datetime.
    Handles both 'Z' suffix and '+00:00' offset.
    """
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)


def is_within_drift(dt: datetime, max_drift_seconds: float = 300.0) -> bool:
    """
    Check if a timestamp is within acceptable clock drift from now.
    Used by Validation Service for received_at clock drift check.
    Default: ±5 minutes (300 seconds).
    """
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = abs((now - dt).total_seconds())
    return diff <= max_drift_seconds


def add_seconds(dt: datetime, seconds: int) -> datetime:
    """Add seconds to a datetime. Returns a UTC-aware datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt + timedelta(seconds=seconds)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_secs = int(seconds % 60)
    return f"{minutes}m {remaining_secs}s"
