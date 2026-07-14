"""
HELIOS OS + SEVRA AI
Database Connection Management - SECTION 10
"""

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from database.config.settings import db_config
from database.encryption.sqlcipher import init_sqlcipher

logger = structlog.get_logger(__name__)

class DatabaseConnectionManager:
    """
    Manages connections and connection pooling for both SQLite and PostgreSQL.
    Follows Section 10: PostgreSQL Architecture (Connection Pooling, Read/Write Separation).
    """
    
    def __init__(self):
        self.sqlite_engine: AsyncEngine | None = None
        self.sqlite_session_factory: async_sessionmaker[AsyncSession] | None = None
        
        self.pg_engine: AsyncEngine | None = None
        self.pg_session_factory: async_sessionmaker[AsyncSession] | None = None
        
        self.pg_read_engine: AsyncEngine | None = None
        self.pg_read_session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self):
        """Initialize all database engines and session factories."""
        
        # 1. Initialize SQLite (Tier 1)
        self.sqlite_engine = create_async_engine(
            db_config.sqlite_dsn,
            echo=False,
            # SQLite specific settings for asyncio
        )
        
        # Apply SQLCipher pragmas synchronously by attaching to the sync engine inside AsyncEngine
        init_sqlcipher(self.sqlite_engine.sync_engine)
        
        self.sqlite_session_factory = async_sessionmaker(
            self.sqlite_engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("sqlite_engine_initialized", path=db_config.SQLITE_PATH)


        # 2. Initialize PostgreSQL Write (Tier 2 Primary)
        self.pg_engine = create_async_engine(
            db_config.postgres_dsn,
            echo=db_config.POSTGRES_ECHO,
            pool_size=db_config.POSTGRES_POOL_SIZE,
            max_overflow=db_config.POSTGRES_MAX_OVERFLOW,
            pool_timeout=db_config.POSTGRES_POOL_TIMEOUT,
            pool_recycle=db_config.POSTGRES_POOL_RECYCLE,
        )
        
        self.pg_session_factory = async_sessionmaker(
            self.pg_engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("postgres_write_engine_initialized")


        # 3. Initialize PostgreSQL Read Replica (Tier 2 Replica - Optional)
        if db_config.postgres_read_dsn:
            self.pg_read_engine = create_async_engine(
                db_config.postgres_read_dsn,
                echo=False,
                pool_size=db_config.POSTGRES_POOL_SIZE,
                max_overflow=db_config.POSTGRES_MAX_OVERFLOW,
                pool_timeout=db_config.POSTGRES_POOL_TIMEOUT,
            )
            
            self.pg_read_session_factory = async_sessionmaker(
                self.pg_read_engine, expire_on_commit=False, class_=AsyncSession
            )
            logger.info("postgres_read_engine_initialized")
        else:
            # Fallback to write engine for reads if replica is not configured
            self.pg_read_engine = self.pg_engine
            self.pg_read_session_factory = self.pg_session_factory
            logger.info("postgres_read_replica_not_configured_falling_back_to_primary")

    async def shutdown(self):
        """Close all connection pools."""
        if self.sqlite_engine:
            await self.sqlite_engine.dispose()
        if self.pg_engine:
            await self.pg_engine.dispose()
        if self.pg_read_engine and self.pg_read_engine is not self.pg_engine:
            await self.pg_read_engine.dispose()
        logger.info("database_connections_closed")

db_manager = DatabaseConnectionManager()
