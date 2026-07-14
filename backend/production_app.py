"""
HELIOS OS + SEVRA AI
Application Entry Point — ASGI App Factory

This module creates and configures the FastAPI application instance.
All middleware, routers, exception handlers, and lifespan events are registered here.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from config.settings import get_settings
from core.exceptions.handlers import register_exception_handlers
from core.logging.logger import configure_logging
from core.middleware.performance import PerformanceMiddleware
from core.middleware.request_id import RequestIDMiddleware
from core.middleware.request_logging import RequestLoggingMiddleware
from core.middleware.security_headers import SecurityHeadersMiddleware
from core.monitoring.metrics import MetricsRegistry
from lifespan import lifespan_handler
from api.router import api_router

logger = structlog.get_logger(__name__)
settings = get_settings()


def create_application() -> FastAPI:
    """
    Application factory. Creates and fully configures the FastAPI instance.
    Called once at startup. Returns a fully wired ASGI application.
    """
    configure_logging(settings)

    app = FastAPI(
        title="HELIOS OS + SEVRA AI",
        description="Real-time Healthcare Intelligence and Patient Monitoring Platform",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan_handler,
    )

    # ── Middleware Stack (order matters — registered in reverse execution order) ──
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # ── Exception Handlers ──
    register_exception_handlers(app)

    # ── API Routers ──
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/api/docs")

    # ── Prometheus Metrics Endpoint ──
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ── Initialize Metrics Registry ──
    MetricsRegistry.initialize()

    logger.info(
        "application_created",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
    )

    return app


# ASGI application instance (used by uvicorn)
app = create_application()
