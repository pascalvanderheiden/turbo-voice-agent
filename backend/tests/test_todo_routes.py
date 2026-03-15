"""Tests for /api/todos REST routes with mocked TodoAgent."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.agents.todo_agent import TodoAgent
from app.main import app
from app.routes.todos import set_todo_agent


@pytest.fixture
def mock_agent():
    agent = AsyncMock(spec=TodoAgent)
    set_todo_agent(agent)
    yield agent
    set_todo_agent(None)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _auth_headers():
    return {"Authorization": "Bearer fake-token"}


class TestListTodos:
    def test_list_returns_todos(self, client, mock_agent):
        mock_agent.handle_function_call.return_value = json.dumps(
            {"todos": [{"id": "t1", "title": "Task 1", "isCompleted": False}]}
        )
        # Patch connection check to allow through
        with _patch_connection():
            resp = client.get("/api/todos", headers=_auth_headers())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_returns_503_when_not_connected(self, client, mock_agent):
        resp = client.get("/api/todos", headers=_auth_headers())
        assert resp.status_code == 503


class TestCreateTodo:
    def test_create(self, client, mock_agent):
        mock_agent.handle_function_call.return_value = json.dumps(
            {"success": True, "todo": {"id": "t1", "title": "New task", "isCompleted": False}}
        )
        with _patch_connection():
            resp = client.post(
                "/api/todos",
                json={"title": "New task"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 201


class TestUpdateTodo:
    def test_update(self, client, mock_agent):
        mock_agent.handle_function_call.return_value = json.dumps(
            {"success": True, "todo": {"id": "t1", "title": "Updated"}}
        )
        with _patch_connection():
            resp = client.put(
                "/api/todos/t1",
                json={"title": "Updated"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200


class TestDeleteTodo:
    def test_delete(self, client, mock_agent):
        mock_agent.handle_function_call.return_value = json.dumps({"success": True})
        with _patch_connection():
            resp = client.delete("/api/todos/t1", headers=_auth_headers())
        assert resp.status_code == 204


class TestAgentUnavailable:
    def test_503_when_no_agent(self, client):
        set_todo_agent(None)
        with _patch_connection():
            resp = client.get("/api/todos", headers=_auth_headers())
        assert resp.status_code == 503


# ── Helpers ──────────────────────────────────────────────────────

from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def _patch_connection():
    """Patch the connection check to simulate a connected user."""
    async def _fake_token(user_id: str):
        return "fake-token"

    with patch("app.routes.user.get_todo_user_token", new=_fake_token):
        yield
