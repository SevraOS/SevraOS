"""
HELIOS OS + SEVRA AI
Authentication Middleware Hook

Optional request-level authentication middleware.
Extracts and validates Bearer tokens on every authenticated request.
Binds user context (user_id, roles, facility_id) to structlog contextvars
so all log entries within the request carry user context automatically.

Note: This middleware is a hook / logger — it does NOT block requests.
      Actual authorization enforcement is done at the endpoint level
      via require_permission() and require_role() FastAPI dependencies.
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.security.jwt import get_jwt_manager
from core.exceptions.base import TokenExpiredException, TokenInvalidException

logger = structlog.get_logger(__name__)

# Paths that never carry auth context (public endpoints)
_PUBLIC_PATHS = frozenset([
    "/metrics",
    "/api/v1/health",
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
])


class AuthContextMiddleware(BaseHTTPMiddleware):
    """
    Extracts JWT bearer token from Authorization header.
    If valid: binds user_id, roles, and facility_id to request state
              and structlog contextvars (for enriched logging).
    If invalid or missing: request.state.user = None (no block).
    Actual authorization enforcement happens at the endpoint dependency level.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.user = None
        request.state.user_roles = []
        request.state.user_facility_id = None

        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token_str = auth_header.removeprefix("Bearer ").strip()

        try:
            jwt_manager = get_jwt_manager()
            payload = jwt_manager.decode_token(token_str)

            # Bind to request state for downstream use
            request.state.user = payload.sub
            request.state.user_roles = payload.roles
            request.state.user_facility_id = payload.facility_id

            # Bind to structlog context — enriches all logs in this request
            structlog.contextvars.bind_contextvars(
                user_id=payload.sub,
                user_roles=",".join(payload.roles),
                facility_id=payload.facility_id or "unknown",
            )

        except (TokenExpiredException, TokenInvalidException):
            # Silently ignore — endpoints enforce auth via dependencies
            pass
        except Exception as exc:
            logger.debug("auth_context_extraction_failed", error=str(exc))

        return await call_next(request)
