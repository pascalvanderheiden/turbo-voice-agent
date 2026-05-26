"""Tests for granular error reporting in /api/sandbox/start probe (Fix 3)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import sandbox


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with sandbox routes."""
    app = FastAPI()
    app.include_router(sandbox.router)

    # Mock sandbox service
    mock_service = MagicMock()
    mock_service.with_user = MagicMock(return_value=mock_service)
    mock_service.set_status = AsyncMock()
    sandbox.set_sandbox_service(mock_service)

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_probe_http_403_returns_error_detail():
    """Probe returns HTTP 403 → error_detail includes status and body."""

    async def _mock_request(*args, **kwargs):
        response = httpx.Response(
            status_code=403,
            text="Forbidden: identity lacks Data Actions role",
        )
        raise httpx.HTTPStatusError("403", request=MagicMock(), response=response)

    mock_client = MagicMock()
    mock_client.request = AsyncMock(side_effect=_mock_request)

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        reachable, active, premium, error_detail = await sandbox._probe_sandbox_health()

    assert reachable is False
    assert error_detail is not None
    assert "HTTP 403" in error_detail
    assert "Forbidden" in error_detail


@pytest.mark.asyncio
async def test_probe_connect_error_returns_network_message():
    """Probe ConnectError → error_detail says pool unreachable."""

    async def _mock_request(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    mock_client = MagicMock()
    mock_client.request = AsyncMock(side_effect=_mock_request)

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        reachable, active, premium, error_detail = await sandbox._probe_sandbox_health()

    assert reachable is False
    assert error_detail == "Pool unreachable (network/DNS issue)"


@pytest.mark.asyncio
async def test_probe_timeout_returns_cold_message():
    """Probe TimeoutException → error_detail says pool cold."""

    async def _mock_request(*args, **kwargs):
        raise httpx.TimeoutException("Request timed out")

    mock_client = MagicMock()
    mock_client.request = AsyncMock(side_effect=_mock_request)

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        reachable, active, premium, error_detail = await sandbox._probe_sandbox_health()

    assert reachable is False
    assert error_detail == "Pool cold (no response within 5s)"


@pytest.mark.asyncio
async def test_start_endpoint_surfaces_error_detail(app: FastAPI):
    """POST /api/sandbox/start returns error_detail in message when probe fails."""
    
    async def _mock_request(*args, **kwargs):
        response = httpx.Response(
            status_code=401,
            text="Unauthorized: token invalid",
        )
        raise httpx.HTTPStatusError("401", request=MagicMock(), response=response)
    
    mock_client = MagicMock()
    mock_client.request = AsyncMock(side_effect=_mock_request)
    
    # Mock request state with no docker_sandbox_svc (session-pool mode)
    class MockState:
        user_id = "test-user"
    
    class MockApp:
        class State:
            docker_sandbox_svc = None  # Session-pool mode
        state = State()
    
    class MockRequest:
        state = MockState()
        app = MockApp()
    
    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        response = await sandbox.start_sandbox(MockRequest())
    
    assert response["status"] == "stopped"
    assert "HTTP 401" in response["message"]
    assert "Unauthorized" in response["message"]
