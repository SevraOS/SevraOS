"""
HELIOS OS + SEVRA AI
Service Container (Dependency Injection)

Centralizes all shared infrastructure clients.
Services access dependencies through this container via FastAPI's DI system.
Future services register their own clients here without modifying existing code.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Database Engine Wrappers ──────────────────────────────────────────────────

class SQLiteEngineWrapper:
    """Wraps the async SQLite engine with lifecycle management."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        import os
        from pathlib import Path

        if settings.SQLITE_PATH != ":memory:":
            Path(settings.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

        from sqlalchemy.pool import StaticPool

        self._engine = create_async_engine(
            settings.sqlite_dsn,
            # aiosqlite does not support pool_size/max_overflow — it uses StaticPool.
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def ping(self) -> None:
        """Verify the SQLite connection is live."""
        if self._engine is None:
            raise RuntimeError("SQLite engine not initialized.")
        async with self._engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("SQLite engine not initialized.")
        return self._session_factory

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("SQLite engine not initialized.")
        return self._engine


class PostgreSQLEngineWrapper:
    """Wraps the async PostgreSQL engine with lifecycle management."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        if not settings.POSTGRES_PASSWORD:
            raise RuntimeError("POSTGRES_PASSWORD is not configured.")

        self._engine = create_async_engine(
            settings.postgres_dsn,
            pool_size=settings.POSTGRES_POOL_SIZE,
            max_overflow=settings.POSTGRES_MAX_OVERFLOW,
            pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
            pool_recycle=settings.POSTGRES_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def ping(self) -> None:
        if self._engine is None:
            raise RuntimeError("PostgreSQL engine not initialized.")
        async with self._engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("PostgreSQL engine not initialized.")
        return self._session_factory

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("PostgreSQL engine not initialized.")
        return self._engine


# ── Redis Client Wrapper ──────────────────────────────────────────────────────

class RedisClientWrapper:
    """Wraps the async Redis client with lifecycle management."""

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None  # type: ignore[type-arg]

    async def initialize(self) -> None:
        self._client = aioredis.from_url(
            settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,
        )

    async def ping(self) -> None:
        if self._client is None:
            raise RuntimeError("Redis client not initialized.")
        await self._client.ping()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> aioredis.Redis:  # type: ignore[type-arg]
        if self._client is None:
            raise RuntimeError("Redis client not initialized.")
        return self._client


# ── Service Container ─────────────────────────────────────────────────────────

class ServiceContainer:
    """
    Central dependency injection container.
    
    Holds all shared infrastructure clients.
    Attached to app.state.container at startup.
    
    Future services extend this container by adding their own client attributes.
    No modification of existing attributes is required when adding new services.
    """

    def __init__(self) -> None:
        self.sqlite_engine = SQLiteEngineWrapper()
        self.postgres_engine = PostgreSQLEngineWrapper()
        self.redis_client = RedisClientWrapper()
        self.postgres_available: bool = True

        # ── Future service slots ───────────────────────────────────────────
        # self.mdil_client = MDILClient()         # Added in MDIL prompt
        # self.ai_model_registry = ModelRegistry() # Added in AI prompt
        # etc.


# ── FastAPI Dependency Functions ──────────────────────────────────────────────

from fastapi import Depends, Request


def get_container(request: Request) -> ServiceContainer:
    """Get the service container from app state."""
    return request.app.state.container


async def get_sqlite_session(
    container: ServiceContainer = Depends(get_container),
) -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency: yields an async SQLite session."""
    async with container.sqlite_engine.get_session()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_postgres_session(
    container: ServiceContainer = Depends(get_container),
) -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency: yields an async PostgreSQL session."""
    if not container.postgres_available:
        raise __import__("core.exceptions.base", fromlist=["ServiceUnavailableException"]).ServiceUnavailableException("postgresql")
    async with container.postgres_engine.get_session()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(
    container: ServiceContainer = Depends(get_container),
) -> aioredis.Redis:  # type: ignore[type-arg]
    """FastAPI dependency: returns the Redis client."""
    return container.redis_client.client
