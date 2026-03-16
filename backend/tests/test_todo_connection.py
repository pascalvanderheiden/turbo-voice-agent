"""Tests for Microsoft To-Do connection endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _auth_headers():
    """Simulate authenticated request state."""
    return {"Authorization": "Bearer fake-token"}


class TestConnectionStatus:
    def test_status_disconnected(self, client):
        resp = client.get("/api/me/connections/microsoft-todo", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False

    def test_status_unauthenticated(self, client):
        # Without auth middleware setting user_id, should still work (default-user or 401)
        resp = client.get("/api/me/connections/microsoft-todo")
        # May be 401 or 200 depending on auth middleware config
        assert resp.status_code in (200, 401)


class TestInitiateConnection:
    def test_connect_auto_connects_when_auth_disabled(self, client):
        resp = client.post("/api/me/connections/microsoft-todo", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        # AUTH_DISABLED=true in test env: auto-connects with mock token
        assert data.get("connected") is True or "authUrl" in data


class TestDisconnect:
    def test_disconnect(self, client):
        resp = client.delete("/api/me/connections/microsoft-todo", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
