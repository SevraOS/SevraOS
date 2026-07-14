"""
HELIOS OS + SEVRA AI
Lifespan Context Manager

Manages the full async startup and shutdown lifecycle of the application.
All infrastructure connections are established here in the correct order.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from startup import run_startup
from shutdown import run_shutdown

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan_handler(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    
    Startup runs before the application accepts requests.
    Shutdown runs after the application stops accepting requests.
    
    This is the single controlled point for all resource lifecycle management.
    """
    logger.info("helios_starting_up", service="helios-backend")
    
    try:
        await run_startup(app)
        logger.info("helios_startup_complete", service="helios-backend")
        yield
    finally:
        logger.info("helios_shutting_down", service="helios-backend")
        await run_shutdown(app)
        logger.info("helios_shutdown_complete", service="helios-backend")
