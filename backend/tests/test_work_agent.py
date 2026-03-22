"""Tests for WorkAgent and WorkMcpClient."""

import json
import pytest

from app.agents.work_agent import WorkAgent
from app.mcp.work_mcp_client import WorkMcpClient


@pytest.fixture
def work_mcp_client():
    """Create a WorkMcpClient instance."""
    return WorkMcpClient()


@pytest.fixture
def work_agent(work_mcp_client: WorkMcpClient):
    """Create a WorkAgent with a mock token resolver."""

    async def mock_token(user_id: str) -> str | None:
        return "mock-token-auth-disabled"

    return WorkAgent(work_mcp_client, get_user_token=mock_token)


@pytest.fixture
def work_agent_no_token(work_mcp_client: WorkMcpClient):
    """Create a WorkAgent with no token resolver (disconnected)."""

    async def no_token(user_id: str) -> str | None:
        return None

    return WorkAgent(work_mcp_client, get_user_token=no_token)


# ── WorkMcpClient tests ──


@pytest.mark.asyncio
async def test_work_mcp_client_stub_ask(work_mcp_client: WorkMcpClient):
    """Stub mode returns a mock response."""
    result = await work_mcp_client.ask(
        question="What meetings do I have today?",
        user_token="mock-token-auth-disabled",
    )
    assert "response" in result
    assert "Mock WorkIQ" in result["response"]
    assert "conversationId" in result


@pytest.mark.asyncio
async def test_work_mcp_client_no_token(work_mcp_client: WorkMcpClient):
    """No token returns an error."""
    result = await work_mcp_client.ask(question="Hello", user_token=None)
    assert "error" in result


@pytest.mark.asyncio
async def test_work_mcp_client_health(work_mcp_client: WorkMcpClient):
    """Health check returns True."""
    assert work_mcp_client.is_healthy
    assert await work_mcp_client.health_check()


@pytest.mark.asyncio
async def test_work_mcp_client_lifecycle(work_mcp_client: WorkMcpClient):
    """Start and stop lifecycle."""
    await work_mcp_client.start()
    assert work_mcp_client.is_healthy
    await work_mcp_client.stop()
    assert not work_mcp_client.is_healthy


# ── WorkAgent tests ──


@pytest.mark.asyncio
async def test_work_agent_tool_definitions(work_agent: WorkAgent):
    """Agent exposes ask_work_question tool."""
    tools = work_agent.tool_definitions
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "ask_work_question"
    params = tools[0]["function"]["parameters"]
    assert "question" in params["properties"]
    assert "file_urls" in params["properties"]
    assert "question" in params["required"]


@pytest.mark.asyncio
async def test_work_agent_ask_question(work_agent: WorkAgent):
    """Ask a work question returns a valid answer."""
    result_str = await work_agent.handle_function_call(
        "ask_work_question",
        json.dumps({"question": "What meetings do I have today?"}),
        user_id="test-user",
    )
    result = json.loads(result_str)
    assert result.get("success") is True
    assert "answer" in result
    assert len(result["answer"]) > 0


@pytest.mark.asyncio
async def test_work_agent_ask_with_file_urls(work_agent: WorkAgent):
    """Ask with file URLs passes through correctly."""
    result_str = await work_agent.handle_function_call(
        "ask_work_question",
        json.dumps({
            "question": "Summarize this document",
            "file_urls": ["https://sharepoint.com/doc.docx"],
        }),
        user_id="test-user",
    )
    result = json.loads(result_str)
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_work_agent_no_token(work_agent_no_token: WorkAgent):
    """Agent without token returns connection error."""
    result_str = await work_agent_no_token.handle_function_call(
        "ask_work_question",
        json.dumps({"question": "What meetings do I have?"}),
        user_id="test-user",
    )
    result = json.loads(result_str)
    assert "error" in result
    assert "not connected" in result["error"].lower()


@pytest.mark.asyncio
async def test_work_agent_unknown_function(work_agent: WorkAgent):
    """Unknown function returns error."""
    result_str = await work_agent.handle_function_call(
        "unknown_function",
        json.dumps({}),
        user_id="test-user",
    )
    result = json.loads(result_str)
    assert "error" in result
    assert "Unknown function" in result["error"]


@pytest.mark.asyncio
async def test_work_agent_invalid_json(work_agent: WorkAgent):
    """Invalid JSON arguments returns error."""
    result_str = await work_agent.handle_function_call(
        "ask_work_question",
        "not-json{{{",
        user_id="test-user",
    )
    result = json.loads(result_str)
    assert "error" in result
