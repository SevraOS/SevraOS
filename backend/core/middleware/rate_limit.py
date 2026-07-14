"""
HELIOS OS + SEVRA AI
Rate Limiting Middleware

Sliding window rate limiter backed by Redis.
Enforces per-IP request limits.
Configurable via settings: RATE_LIMIT_REQUESTS_PER_MINUTE.
"""

from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import ORJSONResponse

logger = structlog.get_logger(__name__)

# Paths exempt from rate limiting
_EXEMPT_PATHS = frozenset(["/metrics", "/api/v1/health/live", "/api/v1/health/ready"])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.

    Algorithm: Fixed window counter per IP per minute.
    Storage: Redis (key: ratelimit:{ip}:{window_minute})
    On Redis failure: fail-open (allow request, log warning).

    Configured by:
        HELIOS_RATE_LIMIT_ENABLED
        HELIOS_RATE_LIMIT_REQUESTS_PER_MINUTE
    """

    def __init__(self, app: object, redis_client: object | None = None) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._redis = redis_client

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        from config.settings import get_settings

        settings = get_settings()

        if not settings.RATE_LIMIT_ENABLED or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Attempt to get Redis from app state
        redis = self._redis
        if redis is None:
            try:
                container = getattr(request.app.state, "container", None)
                if container:
                    redis = container.redis_client.client
            except Exception:
                pass

        if redis is None:
            # Fail-open: no Redis, no rate limiting
            return await call_next(request)

        client_ip = _get_client_ip(request)
        window = int(time.time() // 60)  # 1-minute window
        key = f"ratelimit:{client_ip}:{window}"
        limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE

        try:
            count = await redis.incr(key)
            if count == 1:
                # Set TTL on first request in the window
                await redis.expire(key, 120)  # 2-minute TTL for safety

            if count > limit:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    count=count,
                    limit=limit,
                    path=request.url.path,
                )
                return ORJSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "success": False,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                    },
                )

            # Attach rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
            response.headers["X-RateLimit-Reset"] = str((window + 1) * 60)
            return response

        except Exception as exc:
            # Fail-open on Redis errors
            logger.warning("rate_limit_redis_error", error=str(exc))
            return await call_next(request)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
