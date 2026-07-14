"""
HELIOS OS + SEVRA AI
Centralized Logging Framework

Built on structlog with JSON output, request correlation IDs, and trace support.
All services use this logger — never use Python's standard logging directly.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


def _add_service_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject service-level context into every log entry."""
    from config.settings import get_settings

    settings = get_settings()
    event_dict.setdefault("service", settings.SERVICE_NAME)
    event_dict.setdefault("version", settings.SERVICE_VERSION)
    event_dict.setdefault("environment", settings.ENVIRONMENT)
    event_dict.setdefault("facility_id", settings.FACILITY_ID)
    return event_dict


def _drop_color_message_key(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove uvicorn's color_message key from log output."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(settings: Any) -> None:
    """
    Configure structlog for the application.
    
    JSON format in production/testing.
    Human-readable console format in development.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service_context,
        _drop_color_message_key,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to route through structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.LOG_LEVEL)

    # Silence noisy third-party loggers
    for noisy in ["uvicorn.access", "httpx", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a named logger. Use module __name__ as the name."""
    return structlog.get_logger(name)


def bind_request_context(
    request_id: str,
    correlation_id: str | None = None,
    user_id: str | None = None,
    facility_id: str | None = None,
) -> None:
    """
    Bind request-scoped context to structlog contextvars.
    This context is automatically included in all log entries for this request.
    Call this in middleware at request start; clear it at request end.
    """
    ctx: dict[str, str] = {"request_id": request_id}
    if correlation_id:
        ctx["correlation_id"] = correlation_id
    if user_id:
        ctx["user_id"] = user_id
    if facility_id:
        ctx["facility_id"] = facility_id
    structlog.contextvars.bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear all request-scoped context from structlog contextvars."""
    structlog.contextvars.clear_contextvars()
