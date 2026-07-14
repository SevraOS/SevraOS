"""
HELIOS OS + SEVRA AI — Event Bus Health Monitor

Tracks Redis connectivity, per-stream health, consumer group lag,
pending message counts, DLQ size, and throughput snapshots.
"""
from __future__ import annotations

import time
from typing import Dict, Any

import structlog

from eventbus.client import RedisClientManager
from eventbus.config import config
from eventbus.streams import StreamTopic, ConsumerGroup
from eventbus.metrics import metrics

logger = structlog.get_logger(__name__)


class EventBusHealthService:
    """
    Comprehensive health monitor for the Redis Event Bus.

    Called by the FastAPI /health endpoint and background probes.
    """

    _last_msg_counts: Dict[str, int] = {}
    _last_check_ts: float = 0.0

    @classmethod
    async def check_health(cls) -> Dict[str, Any]:
        """
        Returns a structured health snapshot covering:
        - Redis connectivity
        - Per-stream message counts and lag estimate
        - Consumer group pending-entry-list (PEL) sizes
        - DLQ size
        - Throughput since last probe
        """
        client = RedisClientManager.get_client()
        is_up = await RedisClientManager.is_healthy()

        result: Dict[str, Any] = {
            "status": "up" if is_up else "down",
            "redis_connected": is_up,
            "streams": {},
            "consumer_groups": {},
            "dlq_size": 0,
            "throughput_events_per_sec": 0.0,
        }

        if not is_up:
            return result

        now = time.monotonic()
        elapsed = now - cls._last_check_ts or 1.0

        # ── Per-stream stats ──────────────────────────────────────────────────
        total_now = 0
        for topic in StreamTopic:
            try:
                length = await client.xlen(topic.value)
                result["streams"][topic.name] = {"length": length}
                metrics.set_lag(topic.value, length)
                total_now += length
            except Exception as e:
                result["streams"][topic.name] = {"error": str(e)}

        # Throughput estimate (delta messages / elapsed seconds)
        total_before = sum(cls._last_msg_counts.get(t.value, 0) for t in StreamTopic)
        delta = max(0, total_now - total_before)
        result["throughput_events_per_sec"] = round(delta / elapsed, 2)
        cls._last_msg_counts = {t.value: 0 for t in StreamTopic}
        cls._last_check_ts = now

        # ── Consumer group PEL stats ──────────────────────────────────────────
        group_stream_map = {
            ConsumerGroup.DATABASE_GROUP:    StreamTopic.VITALS,
            ConsumerGroup.AI_GROUP:          StreamTopic.VITALS,
            ConsumerGroup.NOTIFICATION_GROUP: StreamTopic.ALERTS,
            ConsumerGroup.HOSPITAL_GROUP:    StreamTopic.HOSPITAL,
            ConsumerGroup.AUDIT_GROUP:       StreamTopic.AUDIT,
        }

        for group, stream in group_stream_map.items():
            try:
                info = await client.xpending(stream.value, group.value)
                pending_count = info["pending"] if isinstance(info, dict) else 0
                result["consumer_groups"][group.name] = {
                    "stream": stream.name,
                    "pending": pending_count,
                }
                metrics.set_pending(stream.value, group.value, pending_count)
            except Exception as e:
                result["consumer_groups"][group.name] = {"error": str(e)}

        # ── DLQ size ──────────────────────────────────────────────────────────
        try:
            dlq_len = await client.xlen(config.DLQ_STREAM_NAME)
            result["dlq_size"] = dlq_len
        except Exception as e:
            result["dlq_size"] = f"error: {e}"

        return result
