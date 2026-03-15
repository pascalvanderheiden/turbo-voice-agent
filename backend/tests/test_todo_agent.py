"""Tests for TodoAgent — function call handling with mocked MCP client."""

import json
from unittest.mock import AsyncMock

import pytest

from app.agents.todo_agent import TodoAgent
from app.mcp.todo_mcp_client import TodoMcpClient


@pytest.fixture
def mock_mcp():
    return AsyncMock(spec=TodoMcpClient)


@pytest.fixture
def mock_get_token():
    async def _get_token(user_id: str) -> str | None:
        return "fake-refresh-token" if user_id != "disconnected" else None
    return _get_token


@pytest.fixture
def agent(mock_mcp, mock_get_token):
    return TodoAgent(mock_mcp, get_user_token=mock_get_token)


@pytest.mark.asyncio
async def test_create_todo(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {
        "task": {"id": "t1", "title": "Buy groceries", "isCompleted": False}
    }
    result = json.loads(
        await agent.handle_function_call("create_todo", '{"title": "Buy groceries"}', user_id="user1")
    )
    assert result["success"] is True
    assert result["todo"]["title"] == "Buy groceries"
    mock_mcp.call_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_todos(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {
        "tasks": [{"id": "t1", "title": "Task 1"}, {"id": "t2", "title": "Task 2"}]
    }
    result = json.loads(await agent.handle_function_call("get_todos", "{}", user_id="user1"))
    assert len(result["todos"]) == 2


@pytest.mark.asyncio
async def test_get_todo(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {"task": {"id": "t1", "title": "Task 1"}}
    result = json.loads(
        await agent.handle_function_call("get_todo", '{"todo_id": "t1"}', user_id="user1")
    )
    assert result["todo"]["id"] == "t1"


@pytest.mark.asyncio
async def test_update_todo(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {"task": {"id": "t1", "title": "Updated"}}
    result = json.loads(
        await agent.handle_function_call(
            "update_todo", '{"todo_id": "t1", "title": "Updated"}', user_id="user1"
        )
    )
    assert result["success"] is True
    assert result["todo"]["title"] == "Updated"


@pytest.mark.asyncio
async def test_delete_todo(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {"success": True}
    result = json.loads(
        await agent.handle_function_call("delete_todo", '{"todo_id": "t1"}', user_id="user1")
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_complete_todo(agent, mock_mcp):
    mock_mcp.call_tool.return_value = {"task": {"id": "t1", "isCompleted": True}}
    result = json.loads(
        await agent.handle_function_call(
            "complete_todo", '{"todo_id": "t1", "is_completed": true}', user_id="user1"
        )
    )
    assert result["success"] is True
    assert result["todo"]["isCompleted"] is True


@pytest.mark.asyncio
async def test_not_connected_returns_error(agent):
    result = json.loads(
        await agent.handle_function_call("get_todos", "{}", user_id="disconnected")
    )
    assert "error" in result
    assert "not connected" in result["error"].lower()


@pytest.mark.asyncio
async def test_unknown_function(agent, mock_mcp):
    result = json.loads(
        await agent.handle_function_call("unknown_func", "{}", user_id="user1")
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_invalid_arguments(agent):
    result = json.loads(
        await agent.handle_function_call("create_todo", "invalid json{", user_id="user1")
    )
    assert "error" in result
