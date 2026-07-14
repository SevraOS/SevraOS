"""
HELIOS OS + SEVRA AI
Application Shutdown Routines

All infrastructure connections are gracefully closed here.
Order is reverse of startup to prevent dependency conflicts.
"""

import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)


async def run_shutdown(app: FastAPI) -> None:
    """
    Execute all shutdown routines in the correct reverse-dependency order.
    
    Shutdown never raises — it logs errors and continues closing other resources.
    
    Order (reverse of startup):
      1. Close database connections
      2. Close Redis connection
      3. Flush pending logs
    """
    container = getattr(app.state, "container", None)
    if container is None:
        logger.warning("shutdown_no_container_found")
        return

    logger.info("shutdown_begin")

    # Step 1: Close database connections
    await _close_databases(container)

    # Step 2: Close Redis
    await _close_redis(container)

    logger.info("shutdown_complete")


async def _close_databases(container: object) -> None:
    """Close database connection pools."""
    try:
        await container.sqlite_engine.close()
        logger.info("sqlite_disconnected")
    except Exception as exc:
        logger.error("sqlite_close_error", error=str(exc))

    try:
        if getattr(container, "postgres_available", False):
            await container.postgres_engine.close()
            logger.info("postgres_disconnected")
    except Exception as exc:
        logger.error("postgres_close_error", error=str(exc))


async def _close_redis(container: object) -> None:
    """Close Redis connection pool."""
    try:
        await container.redis_client.close()
        logger.info("redis_disconnected")
    except Exception as exc:
        logger.error("redis_close_error", error=str(exc))
