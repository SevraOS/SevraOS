"""
HELIOS OS + SEVRA AI
Application Startup Routines

All infrastructure connections are initialized here in dependency order.
Each startup step is atomic — failure in any step aborts the entire startup.
"""

import structlog
from fastapi import FastAPI

from config.settings import get_settings
from core.dependencies.container import ServiceContainer

logger = structlog.get_logger(__name__)
settings = get_settings()


async def run_startup(app: FastAPI) -> None:
    """
    Execute all startup routines in the correct dependency order.
    
    Order:
      1. Initialize service container
      2. Connect to Redis
      3. Connect to database (SQLite + PostgreSQL)
      4. Verify external dependencies (non-blocking — logs warnings only)
      5. Attach container to app state
    """
    logger.info("startup_begin")

    # Step 1: Initialize the service container
    container = ServiceContainer()

    # Step 2: Redis connection
    await _connect_redis(container)

    # Step 3: Database connections
    await _connect_databases(container)

    # Step 4: Verify optional external dependencies (non-blocking)
    await _verify_external_deps(container)

    # Step 5: Attach container to app state for dependency injection
    app.state.container = container

    # Step 6: Register health checks so /health reflects real dependency state
    await _register_health_checks(container)

    logger.info("startup_complete")


async def _register_health_checks(container: "ServiceContainer") -> None:
    """Wire concrete health checks into the singleton HealthAggregator."""
    from core.monitoring.health import (
        get_health_aggregator,
        RedisHealthCheck,
        SQLiteHealthCheck,
        PostgreSQLHealthCheck,
    )

    aggregator = get_health_aggregator()
    aggregator.register(RedisHealthCheck(container.redis_client.client))
    aggregator.register(SQLiteHealthCheck(container.sqlite_engine))
    aggregator.register(
        PostgreSQLHealthCheck(
            engine=container.postgres_engine,
            is_available=container.postgres_available,
        )
    )
    logger.info("health_checks_registered", count=3)


async def _connect_redis(container: "ServiceContainer") -> None:
    """Establish Redis connection pool."""
    try:
        await container.redis_client.initialize()
        await container.redis_client.ping()
        logger.info("redis_connected", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    except Exception as exc:
        logger.error("redis_connection_failed", error=str(exc))
        raise RuntimeError(f"Redis connection failed: {exc}") from exc


async def _connect_databases(container: "ServiceContainer") -> None:
    """Initialize SQLite and PostgreSQL connections."""
    # SQLite — always required (offline-first)
    try:
        await container.sqlite_engine.initialize()
        logger.info("sqlite_connected", path=settings.SQLITE_PATH)
    except Exception as exc:
        logger.error("sqlite_connection_failed", error=str(exc))
        raise RuntimeError(f"SQLite connection failed: {exc}") from exc

    # PostgreSQL — optional at startup (offline-first design)
    try:
        await container.postgres_engine.initialize()
        logger.info("postgres_connected", host=settings.POSTGRES_HOST)
    except Exception as exc:
        logger.warning(
            "postgres_connection_failed_degraded_mode",
            error=str(exc),
            note="System will operate in offline mode. SQLite is primary store.",
        )
        container.postgres_available = False


async def _verify_external_deps(container: "ServiceContainer") -> None:
    """Verify optional external dependencies. Logs warnings — never raises."""
    logger.info("external_dependency_check_skipped_in_foundation")

    # Compatibility: Initialize dashboard's legacy db_manager and websocket
    import os
    import asyncio
    from database.services.connection import db_manager
    from dashboard.websocket.manager import ws_manager
    
    dsn = os.environ.get("HELIOS_POSTGRES_DSN")
    if dsn:
        db_manager.initialize_postgres(dsn)
    
    # Store the websocket task on the container so it can be canceled later if needed
    container.ws_task = asyncio.create_task(ws_manager.start_redis_listener())
    logger.info("dashboard_compatibility_services_started")
