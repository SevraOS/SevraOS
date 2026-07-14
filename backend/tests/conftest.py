"""
HELIOS OS + SEVRA AI
Test Configuration and Fixtures

Provides shared fixtures for all tests:
  - Async test client
  - Database sessions (SQLite in-memory)
  - Redis mock
  - JWT tokens for each role
  - Factory helpers
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from config.settings import get_settings
from core.security.jwt import JWTManager
from core.security.rbac import Role


# ── Session Configuration ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy:
    return asyncio.DefaultEventLoopPolicy()


# ── Settings Override ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def override_settings() -> Generator[None, None, None]:
    """Force testing settings for all tests."""
    import os
    os.environ["HELIOS_ENVIRONMENT"] = "testing"
    # Clear the lru_cache so testing settings are loaded
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── Application ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create a test application instance."""
    from app import create_application
    return create_application()


# ── HTTP Client ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client.
    Uses ASGI transport — no real network connections.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── JWT Token Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def jwt_manager() -> JWTManager:
    return JWTManager()


@pytest.fixture
def admin_token(jwt_manager: JWTManager) -> str:
    """Valid JWT access token for the Admin role."""
    pair = jwt_manager.create_token_pair(
        user_id="test-admin-001",
        roles=[Role.ADMIN],
        facility_id="FACILITY-001",
    )
    return pair.access_token


@pytest.fixture
def clinician_token(jwt_manager: JWTManager) -> str:
    """Valid JWT access token for the Clinician role."""
    pair = jwt_manager.create_token_pair(
        user_id="test-clinician-001",
        roles=[Role.CLINICIAN],
        facility_id="FACILITY-001",
    )
    return pair.access_token


@pytest.fixture
def nurse_token(jwt_manager: JWTManager) -> str:
    """Valid JWT access token for the Nurse role."""
    pair = jwt_manager.create_token_pair(
        user_id="test-nurse-001",
        roles=[Role.NURSE],
        facility_id="FACILITY-001",
    )
    return pair.access_token


@pytest.fixture
def auditor_token(jwt_manager: JWTManager) -> str:
    """Valid JWT access token for the Auditor role."""
    pair = jwt_manager.create_token_pair(
        user_id="test-auditor-001",
        roles=[Role.AUDITOR],
        facility_id="FACILITY-001",
    )
    return pair.access_token


@pytest.fixture
def auth_headers_admin(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_clinician(clinician_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clinician_token}"}


# ── Mock Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client for unit tests."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_sqlite_session() -> AsyncMock:
    """Mock SQLite session for unit tests."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_postgres_session() -> AsyncMock:
    """Mock PostgreSQL session for unit tests."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session
