"""Tests for pool 4xx/5xx error surfacing in _sandbox_exec (Fix 2)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.agents.dev_agent import DevAgent, _pipeline_outputs


@pytest.fixture(autouse=True)
def _clear_output_buffers() -> None:
    """Ensure each test starts with clean pipeline output buffers."""
    _pipeline_outputs.clear()
    yield
    _pipeline_outputs.clear()


@pytest.fixture
def agent() -> DevAgent:
    return DevAgent(dev_service=MagicMock())


@pytest.mark.asyncio
async def test_http_403_raises_runtime_error_with_diagnostic(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 403 → RuntimeError with diagnostic message."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        # Simulate pool returning 403 Forbidden
        response = httpx.Response(
            status_code=403,
            text="Forbidden: backend identity lacks RBAC role",
        )
        raise httpx.HTTPStatusError("403", request=MagicMock(), response=response)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

    # Initialize output buffer so the error gets appended
    task_id = "task-403"
    _pipeline_outputs[task_id] = []

    with pytest.raises(RuntimeError) as exc_info:
        await agent._sandbox_exec(
            task_id=task_id,
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    err_msg = str(exc_info.value)
    assert "HTTP 403" in err_msg
    assert "RBAC" in err_msg
    
    # Verify error was appended to output buffer (after stage marker)
    buf = _pipeline_outputs[task_id]
    assert len(buf) >= 1
    # Find the stderr entry
    stderr_entries = [e for e in buf if e["type"] == "stderr"]
    assert len(stderr_entries) == 1
    assert "HTTP 403" in stderr_entries[0]["data"]


@pytest.mark.asyncio
async def test_http_429_raises_runtime_error_with_diagnostic(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 429 (concurrency cap hit) → RuntimeError with diagnostic."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = httpx.Response(
            status_code=429,
            text="Concurrency limit reached",
        )
        raise httpx.HTTPStatusError("429", request=MagicMock(), response=response)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

    task_id = "task-429"
    _pipeline_outputs[task_id] = []

    with pytest.raises(RuntimeError) as exc_info:
        await agent._sandbox_exec(
            task_id=task_id,
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    err_msg = str(exc_info.value)
    assert "HTTP 429" in err_msg
    assert "Concurrency limit" in err_msg


@pytest.mark.asyncio
async def test_http_500_raises_runtime_error(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 500 → RuntimeError with truncated body."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        # Simulate pool returning 500 with long body
        long_body = "Internal server error: " + "x" * 600
        response = httpx.Response(status_code=500, text=long_body)
        raise httpx.HTTPStatusError("500", request=MagicMock(), response=response)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

    task_id = "task-500"
    _pipeline_outputs[task_id] = []

    with pytest.raises(RuntimeError) as exc_info:
        await agent._sandbox_exec(
            task_id=task_id,
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    err_msg = str(exc_info.value)
    assert "HTTP 500" in err_msg
    # Body should be truncated to 500 chars
    assert len(err_msg) < 700
