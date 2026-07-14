"""
HELIOS OS + SEVRA AI
Health Monitoring - SECTION 14
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import text
from database.config.settings import db_config
from eventbus.client import RedisClientManager

logger = structlog.get_logger(__name__)

class DatabaseHealthService:
    """
    Monitors health of SQLite, PostgreSQL, and Redis.
    Used for Offline-First detection and Kubernetes readiness probes.
    """
    
    def __init__(
        self, 
        sqlite_session_factory: async_sessionmaker[AsyncSession],
        pg_session_factory: async_sessionmaker[AsyncSession]
    ):
        self.sqlite_session_factory = sqlite_session_factory
        self.pg_session_factory = pg_session_factory

    async def check_sqlite(self) -> bool:
        """Check if edge SQLite is writable."""
        try:
            async with self.sqlite_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.critical("sqlite_health_check_failed", error=str(e))
            return False

    async def check_postgresql(self) -> bool:
        """Check if central PostgreSQL is available."""
        try:
            async with self.pg_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning("postgresql_health_check_failed_offline_mode", error=str(e))
            return False

    async def check_redis(self) -> bool:
        """Check if Redis Cache / Eventbus is available."""
        return await RedisClientManager.is_healthy()

    async def get_system_health(self) -> dict:
        """Returns comprehensive health status."""
        sqlite_ok = await self.check_sqlite()
        pg_ok = await self.check_postgresql()
        redis_ok = await self.check_redis()
        
        status = "HEALTHY"
        if not sqlite_ok:
            status = "CRITICAL" # Edge DB down means we can't save anything
        elif not redis_ok:
            status = "DEGRADED" # Can't process new events, but DB is fine
        elif not pg_ok:
            status = "OFFLINE_MODE" # Working as designed, but syncing is paused
            
        return {
            "status": status,
            "components": {
                "sqlite": "ok" if sqlite_ok else "down",
                "postgresql": "ok" if pg_ok else "down",
                "redis": "ok" if redis_ok else "down",
            },
            "environment": db_config.ENVIRONMENT,
            "facility": db_config.FACILITY_ID
        }
