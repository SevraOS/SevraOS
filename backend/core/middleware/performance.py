"""
HELIOS OS + SEVRA AI
Performance Monitoring Middleware

Records HTTP request duration and updates Prometheus histograms.
Tracks per-endpoint latency for SLA monitoring.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.monitoring.metrics import MetricsRegistry


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Records request duration to Prometheus histogram.
    Skips /metrics endpoint to avoid self-measurement noise.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        try:
            MetricsRegistry.http_request_duration.labels(
                method=request.method,
                path=_normalize_path(request.url.path),
                status_code=str(response.status_code),
            ).observe(duration)

            MetricsRegistry.http_requests_total.labels(
                method=request.method,
                path=_normalize_path(request.url.path),
                status_code=str(response.status_code),
            ).inc()
        except Exception:
            pass  # Never let metrics collection break request handling

        return response


def _normalize_path(path: str) -> str:
    """
    Normalize URL path for Prometheus label cardinality control.
    Replaces dynamic segments (UUIDs, IDs) with placeholders.
    e.g., /api/v1/patients/uuid-123 → /api/v1/patients/{id}
    """
    import re

    # Replace UUIDs
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{uuid}",
        path,
    )
    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    return path
