"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Health endpoint test suite."""

    async def test_liveness_returns_200(self, client: AsyncClient) -> None:
        """Liveness probe must always return 200 if the process is alive."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True

    async def test_full_health_returns_valid_structure(self, client: AsyncClient) -> None:
        """Full health endpoint must return correct schema."""
        response = await client.get("/api/v1/health")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data

    async def test_readiness_returns_valid_structure(self, client: AsyncClient) -> None:
        """Readiness probe must return ready field."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "ready" in data or "status" in data
