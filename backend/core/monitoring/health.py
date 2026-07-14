"""
HELIOS OS + SEVRA AI
Health Check Framework

Provides a composable health check system.
Each dependency implements HealthCheck and is registered with HealthAggregator.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

import structlog

from core.responses.models import HealthResponse, ServiceHealthStatus

logger = structlog.get_logger(__name__)


# ── Health Check Interface ────────────────────────────────────────────────────

class HealthCheck(ABC):
    """Base class for all health checks. Implement check() for each dependency."""

    name: str

    @abstractmethod
    async def check(self) -> ServiceHealthStatus:
        """Perform the health check and return status."""
        ...


# ── Concrete Health Checks ────────────────────────────────────────────────────

class RedisHealthCheck(HealthCheck):
    name = "redis"

    def __init__(self, redis_client: object) -> None:
        self._client = redis_client

    async def check(self) -> ServiceHealthStatus:
        start = time.perf_counter()
        try:
            await self._client.ping()  # type: ignore[attr-defined]
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ServiceHealthStatus(
                name=self.name, status="healthy", latency_ms=latency_ms
            )
        except Exception as exc:
            return ServiceHealthStatus(
                name=self.name,
                status="unhealthy",
                message=str(exc),
            )


class SQLiteHealthCheck(HealthCheck):
    name = "sqlite"

    def __init__(self, engine: object) -> None:
        self._engine = engine

    async def check(self) -> ServiceHealthStatus:
        start = time.perf_counter()
        try:
            await self._engine.ping()  # type: ignore[attr-defined]
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ServiceHealthStatus(
                name=self.name, status="healthy", latency_ms=latency_ms
            )
        except Exception as exc:
            return ServiceHealthStatus(
                name=self.name,
                status="unhealthy",
                message=str(exc),
            )


class PostgreSQLHealthCheck(HealthCheck):
    name = "postgresql"

    def __init__(self, engine: object, is_available: bool = True) -> None:
        self._engine = engine
        self._is_available = is_available

    async def check(self) -> ServiceHealthStatus:
        if not self._is_available:
            return ServiceHealthStatus(
                name=self.name,
                status="degraded",
                message="PostgreSQL not available. Operating in offline mode.",
            )
        start = time.perf_counter()
        try:
            await self._engine.ping()  # type: ignore[attr-defined]
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ServiceHealthStatus(
                name=self.name, status="healthy", latency_ms=latency_ms
            )
        except Exception as exc:
            return ServiceHealthStatus(
                name=self.name,
                status="unhealthy",
                message=str(exc),
            )


# ── Health Aggregator ─────────────────────────────────────────────────────────

class HealthAggregator:
    """
    Runs all registered health checks concurrently and aggregates results.
    
    Status rules:
      - "healthy": all checks pass
      - "degraded": at least one check is degraded (system functional with limitations)
      - "unhealthy": at least one check is unhealthy (system impaired)
    """

    def __init__(self, timeout: float = 5.0) -> None:
        self._checks: list[HealthCheck] = []
        self._timeout = timeout

    def register(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks.append(check)

    async def run(self) -> HealthResponse:
        """Run all health checks concurrently and return aggregated health."""
        from config.settings import get_settings
        settings = get_settings()

        if not self._checks:
            return HealthResponse(
                status="healthy",
                version=settings.SERVICE_VERSION,
                environment=settings.ENVIRONMENT,
            )

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[check.check() for check in self._checks]),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.error("health_check_timeout", timeout=self._timeout)
            results = [
                ServiceHealthStatus(
                    name=check.name,
                    status="unhealthy",
                    message="Health check timed out",
                )
                for check in self._checks
            ]

        statuses = [r.status for r in results]
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthResponse(
            status=overall,
            version=settings.SERVICE_VERSION,
            environment=settings.ENVIRONMENT,
            dependencies=list(results),
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_health_aggregator: HealthAggregator | None = None


def get_health_aggregator() -> HealthAggregator:
    global _health_aggregator
    if _health_aggregator is None:
        from config.settings import get_settings
        settings = get_settings()
        _health_aggregator = HealthAggregator(timeout=settings.HEALTH_CHECK_TIMEOUT)
    return _health_aggregator
