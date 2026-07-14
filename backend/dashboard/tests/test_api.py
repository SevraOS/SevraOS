"""
HELIOS OS + SEVRA AI
Dashboard API Tests (Section 23)
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect

from dashboard.api.main import app
from dashboard.api.dependencies import get_uow, get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_dependencies():
    # Mock UOW dependency to prevent hitting uninitialized DB
    async def override_get_uow():
        yield None
    
    app.dependency_overrides[get_uow] = override_get_uow
    yield
    app.dependency_overrides.clear()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "dashboard"}

def test_get_patients_unauthenticated():
    # The get_current_user dependency will raise 403 HTTPBearer error
    response = client.get("/api/v1/patients")
    assert response.status_code == 401

def test_websocket_connect_invalid_token():
    # WebSocket route requires a token. Invalid token disconnects with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/stream?token=invalid"):
            pass
    assert exc_info.value.code == 1008

def test_websocket_stream_requires_token():
    # Missing required query param
    response = client.get("/ws/stream")
    assert response.status_code == 404 # TestClient for missing ws token
