"""
HELIOS OS + SEVRA AI
Prometheus Metrics Registry

Centralizes all Prometheus metric definitions.
Services import from here — never create metrics ad-hoc in endpoints.
All metrics use the helios_ prefix per naming convention.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info


class MetricsRegistry:
    """
    Singleton metrics registry.
    Call MetricsRegistry.initialize() once at application startup.
    All metrics are class-level attributes for global access.
    """

    # ── HTTP Metrics ──────────────────────────────────────────────────────────
    http_requests_total: Counter
    http_request_duration: Histogram

    # ── Service Health ────────────────────────────────────────────────────────
    service_up: Gauge
    service_info: Info

    # ── Database Metrics ──────────────────────────────────────────────────────
    db_sqlite_writes_total: Counter
    db_postgres_writes_total: Counter
    db_sync_pending_total: Gauge
    db_sync_failures_total: Counter

    # ── Redis Metrics ─────────────────────────────────────────────────────────
    redis_operations_total: Counter
    redis_operation_duration: Histogram

    # ── Security Metrics ──────────────────────────────────────────────────────
    auth_attempts_total: Counter
    auth_failures_total: Counter
    active_sessions_total: Gauge

    # ── Pipeline Metrics (populated by future services) ───────────────────────
    pipeline_events_total: Counter
    pipeline_errors_total: Counter

    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize all metrics. Must be called once at startup."""
        if cls._initialized:
            return

        cls.http_requests_total = Counter(
            "helios_http_requests_total",
            "Total number of HTTP requests",
            ["method", "path", "status_code"],
        )
        cls.http_request_duration = Histogram(
            "helios_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "path", "status_code"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )
        cls.service_up = Gauge(
            "helios_up",
            "Service availability (1 = up, 0 = down)",
            ["service"],
        )
        cls.service_info = Info(
            "helios_service",
            "HELIOS service build information",
        )
        cls.db_sqlite_writes_total = Counter(
            "helios_db_sqlite_writes_total",
            "Total SQLite write operations",
            ["table", "operation"],
        )
        cls.db_postgres_writes_total = Counter(
            "helios_db_postgres_writes_total",
            "Total PostgreSQL write operations",
            ["table", "operation"],
        )
        cls.db_sync_pending_total = Gauge(
            "helios_db_sync_pending_total",
            "Number of records pending sync from SQLite to PostgreSQL",
        )
        cls.db_sync_failures_total = Counter(
            "helios_db_sync_failures_total",
            "Total database sync failures",
        )
        cls.redis_operations_total = Counter(
            "helios_redis_operations_total",
            "Total Redis operations",
            ["operation", "stream"],
        )
        cls.redis_operation_duration = Histogram(
            "helios_redis_operation_duration_seconds",
            "Redis operation duration in seconds",
            ["operation"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
        )
        cls.auth_attempts_total = Counter(
            "helios_auth_attempts_total",
            "Total authentication attempts",
            ["outcome"],  # success | failure
        )
        cls.auth_failures_total = Counter(
            "helios_auth_failures_total",
            "Total authentication failures",
            ["reason"],
        )
        cls.active_sessions_total = Gauge(
            "helios_active_sessions_total",
            "Number of active user sessions",
        )
        cls.pipeline_events_total = Counter(
            "helios_pipeline_events_total",
            "Total events processed by pipeline stage",
            ["stage", "status"],
        )
        cls.pipeline_errors_total = Counter(
            "helios_pipeline_errors_total",
            "Total pipeline processing errors",
            ["stage", "error_type"],
        )

        # Mark service as up
        from config.settings import get_settings
        settings = get_settings()
        cls.service_up.labels(service=settings.SERVICE_NAME).set(1)
        cls.service_info.info({
            "version": settings.SERVICE_VERSION,
            "environment": settings.ENVIRONMENT,
        })

        cls._initialized = True
