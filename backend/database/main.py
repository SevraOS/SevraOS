"""
HELIOS OS + SEVRA AI
Database Service Entrypoint

Integrates Redis Event Bus -> Database Consumer -> SQLite -> Sync Engine -> PostgreSQL.
"""

import asyncio
import structlog
import signal
from typing import Any

from database.config.settings import db_config
from database.services.connection import db_manager
from database.health.health_server import DatabaseHealthService
from database.sync.engine import SyncEngine
from database.consumers.vitals_consumer import VitalsDatabaseConsumer
from database.services.recovery import Orchestrator
from database.services.uow import UnitOfWork

logger = structlog.get_logger(__name__)

async def async_main():
    """Main async entrypoint for the Database Service."""
    logger.info("starting_database_service", environment=db_config.ENVIRONMENT)

    # 1. Initialize Database Connections
    await db_manager.initialize()

    # 2. Setup Unit of Work Factory (SQLite is primary write target)
    def uow_factory() -> UnitOfWork:
        if not db_manager.sqlite_session_factory:
            raise RuntimeError("Database not initialized")
        return UnitOfWork(db_manager.sqlite_session_factory)

    # 3. Initialize Components
    health_service = DatabaseHealthService(
        sqlite_session_factory=db_manager.sqlite_session_factory, # type: ignore
        pg_session_factory=db_manager.pg_session_factory # type: ignore
    )
    
    sync_engine = SyncEngine(
        sqlite_session_factory=db_manager.sqlite_session_factory, # type: ignore
        pg_session_factory=db_manager.pg_session_factory # type: ignore
    )
    
    # Instantiate consumers
    vitals_consumer = VitalsDatabaseConsumer(uow_factory=uow_factory)
    
    # 4. Initialize Orchestrator
    orchestrator = Orchestrator(
        health_service=health_service,
        sync_engine=sync_engine,
        consumers=[vitals_consumer]
    )

    # 5. Handle graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_sigint(sig: Any, frame: Any):
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    # 6. Start the Orchestrator (which starts everything else based on health)
    await orchestrator.start()
    
    # 7. Wait until shutdown requested
    await shutdown_event.wait()
    
    # 8. Graceful Teardown
    logger.info("shutting_down_services")
    await orchestrator.stop()
    await db_manager.shutdown()
    logger.info("database_service_shutdown_complete")


def main():
    """Synchronous entrypoint wrapper."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical("fatal_database_service_error", error=str(e), exc_info=True)
        raise

if __name__ == "__main__":
    main()
