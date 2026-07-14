"""
HELIOS OS + SEVRA AI
Request ID Middleware

Generates or propagates a unique X-Request-ID for every incoming request.
Binds the ID to structlog contextvars so all log entries in this request
automatically include the request_id.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging.logger import bind_request_context, clear_request_context

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to every request.
    
    - Uses the incoming X-Request-ID if provided (from API gateway / load balancer).
    - Generates a new UUID v4 if not present.
    - Propagates the ID in the response header.
    - Binds the ID to structlog contextvars for the duration of the request.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)

        # Bind to structlog — all logs in this request include request_id
        bind_request_context(
            request_id=request_id,
            correlation_id=correlation_id,
        )

        # Store on request state for downstream access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
        finally:
            clear_request_context()

        response.headers[REQUEST_ID_HEADER] = request_id
        if correlation_id:
            response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
