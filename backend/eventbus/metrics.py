"""
HELIOS OS + SEVRA AI — Event Bus Metrics
Full Prometheus integration with counters, histograms, and gauges.
"""
from prometheus_client import Counter, Histogram, Gauge

# ── Counters ───────────────────────────────────────────────────────────────────

events_published_total = Counter(
    "sevra_events_published_total",
    "Total events published to Redis Streams",
    ["stream"]
)

events_consumed_total = Counter(
    "sevra_events_consumed_total",
    "Total events successfully processed by a consumer group",
    ["consumer_group"]
)

consumer_errors_total = Counter(
    "sevra_consumer_errors_total",
    "Total events that failed processing (before DLQ)",
    ["consumer_group"]
)

dlq_events_total = Counter(
    "sevra_dlq_events_total",
    "Total events moved to the Dead Letter Queue"
)

# ── Histograms ─────────────────────────────────────────────────────────────────

consumer_processing_time = Histogram(
    "sevra_consumer_processing_seconds",
    "Time taken to process a single event in a consumer group",
    ["consumer_group"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# ── Gauges ─────────────────────────────────────────────────────────────────────

pending_messages_total = Gauge(
    "sevra_pending_messages_total",
    "Number of unacknowledged (pending) messages in a consumer group",
    ["stream", "consumer_group"]
)

stream_lag_total = Gauge(
    "sevra_stream_lag_total",
    "Estimated lag (unconsumed messages) per stream",
    ["stream"]
)

dlq_size_current = Gauge(
    "sevra_dlq_size_current",
    "Current number of messages in the Dead Letter Queue"
)


# ── Helper façade (matches prior interface used in producer/consumer/dlq) ──────

class EventBusMetrics:
    """Thin façade that delegates to Prometheus client instruments."""

    @staticmethod
    def inc_published(stream: str) -> None:
        events_published_total.labels(stream=stream).inc()

    @staticmethod
    def inc_consumed(group: str) -> None:
        events_consumed_total.labels(consumer_group=group).inc()

    @staticmethod
    def inc_error(group: str) -> None:
        consumer_errors_total.labels(consumer_group=group).inc()

    @staticmethod
    def inc_dlq() -> None:
        dlq_events_total.inc()
        dlq_size_current.inc()

    @staticmethod
    def observe_processing(group: str, seconds: float) -> None:
        consumer_processing_time.labels(consumer_group=group).observe(seconds)

    @staticmethod
    def set_pending(stream: str, group: str, count: int) -> None:
        pending_messages_total.labels(stream=stream, consumer_group=group).set(count)

    @staticmethod
    def set_lag(stream: str, count: int) -> None:
        stream_lag_total.labels(stream=stream).set(count)


metrics = EventBusMetrics()
