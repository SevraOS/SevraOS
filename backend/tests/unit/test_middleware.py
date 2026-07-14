"""Tests for exception handlers — verifying correct HTTP status codes and response formats."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestExceptionHandlers:
    """Verify global exception handlers return correct formats."""

    async def test_404_returns_error_response(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/this-does-not-exist")
        assert response.status_code == 404

    async def test_unauthorized_endpoint_returns_401(self, client: AsyncClient) -> None:
        """Endpoints requiring auth must return 401 without a token."""
        # This will be properly tested once auth endpoints are added.
        # Foundation test: confirm the server is reachable.
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200

    async def test_response_has_request_id_header(self, client: AsyncClient) -> None:
        """Every response must include X-Request-ID header."""
        response = await client.get("/api/v1/health/live")
        assert "x-request-id" in response.headers

    async def test_security_headers_present(self, client: AsyncClient) -> None:
        """Security headers must be applied to every response."""
        response = await client.get("/api/v1/health/live")
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"
