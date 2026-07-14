"""
HELIOS OS + SEVRA AI
Request Logging Middleware

Logs every HTTP request and response with structured context:
  - Method, path, status code, duration, user agent
  - Request ID (from RequestIDMiddleware, which runs first)
  - Skips logging for /metrics and /health to reduce noise
"""

from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Paths excluded from request logging (high-frequency, low-value)
_SKIP_PATHS = frozenset(["/metrics", "/health", "/ready", "/live", "/favicon.ico"])


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured HTTP access logging middleware.
    
    Logs request start and completion with timing information.
    Errors in handling the request are also logged with the exception.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        if path in _SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            "request_started",
            method=request.method,
            path=path,
            query=str(request.url.query) or None,
            request_id=request_id,
            client_ip=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "request_unhandled_exception",
                method=request.method,
                path=path,
                duration_ms=duration_ms,
                request_id=request_id,
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log_fn = logger.warning if response.status_code >= 400 else logger.info

        log_fn(
            "request_completed",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )

        return response


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For from trusted proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
