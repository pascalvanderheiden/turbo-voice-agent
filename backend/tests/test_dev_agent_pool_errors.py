"""Tests for pool 4xx/5xx error surfacing and transient retries in _sandbox_exec."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from azure.core.credentials import AccessToken

from app.agents import dev_agent as dev_agent_mod
from app.agents.dev_agent import DevAgent, _pipeline_outputs
from app.services.session_sandbox_client import SessionSandboxClient

ENDPOINT = "https://pool.example.com"


class _SSESuccessResponse:
    status_code = 200

    async def aiter_lines(self) -> AsyncIterator[str]:
        yield 'data: {"type":"stdout","data":"ok\\n"}'
        yield 'data: {"type":"exit","code":0}'


class _RespxSandboxClient:
    def __init__(self) -> None:
        credential = MagicMock()
        credential.get_token.return_value = AccessToken("tok-test", int(time.time()) + 3600)
        self._client = SessionSandboxClient(endpoint=ENDPOINT, credential=credential)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self._client.request(method, path, **kwargs)

    @asynccontextmanager
    async def stream_response(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[_SSESuccessResponse]:
        yield _SSESuccessResponse()

    async def stop_session(self, identifier: str, *, reason: str = "complete") -> None:
        return None


@pytest.fixture(autouse=True)
def _clear_output_buffers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts with clean buffers and fast retry sleeps."""

    async def _no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(dev_agent_mod.asyncio, "sleep", _no_sleep)
    _pipeline_outputs.clear()
    yield
    _pipeline_outputs.clear()


@pytest.fixture
def agent() -> DevAgent:
    return DevAgent(dev_service=MagicMock())


def _stderr_entries(task_id: str) -> list[dict]:
    return [entry for entry in _pipeline_outputs[task_id] if entry["type"] == "stderr"]


@pytest.mark.asyncio
async def test_http_403_raises_runtime_error_with_diagnostic(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 403 → RuntimeError with diagnostic message."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = httpx.Response(
            status_code=403,
            text="Forbidden: backend identity lacks RBAC role",
        )
        raise httpx.HTTPStatusError("403", request=MagicMock(), response=response)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

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
    stderr_entries = _stderr_entries(task_id)
    assert len(stderr_entries) == 1
    assert "HTTP 403" in stderr_entries[0]["data"]


@pytest.mark.asyncio
async def test_http_429_raises_runtime_error_with_diagnostic(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 429 repeatedly → RuntimeError with diagnostic after retries."""

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
    assert client.request.call_count == 3


@pytest.mark.asyncio
async def test_http_500_raises_runtime_error(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 500 repeatedly → RuntimeError with truncated body after retries."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
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
    assert len(err_msg) < 700
    assert client.request.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_transient_503_twice_then_200_succeeds_without_stderr(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 503 twice, then 200 → succeeds and does not emit stderr."""
    route = respx.post(f"{ENDPOINT}/tasks").mock(
        side_effect=[
            httpx.Response(503, text="allocator warming up"),
            httpx.Response(503, text="allocator still warming up"),
            httpx.Response(200, json={"id": "sandbox-task-ok"}),
        ]
    )
    monkeypatch.setattr(agent, "_sandbox_client", _RespxSandboxClient)

    task_id = "task-503-retry"
    _pipeline_outputs[task_id] = []

    output = await agent._sandbox_exec(
        task_id=task_id,
        command="echo hello",
        args=[],
        stage_label="implement",
    )

    assert output == "ok\n"
    assert route.call_count == 3
    assert _stderr_entries(task_id) == []


@pytest.mark.asyncio
@respx.mock
async def test_allocator_body_fails_after_three_attempts_and_emits_stderr(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allocator error body with 500 three times → terminal error and stderr."""
    body = "Error happened when allocating pod for identifier task in pool sp-sandbox"
    route = respx.post(f"{ENDPOINT}/tasks").mock(return_value=httpx.Response(500, text=body))
    monkeypatch.setattr(agent, "_sandbox_client", _RespxSandboxClient)

    task_id = "task-allocator-exhausted"
    _pipeline_outputs[task_id] = []

    with pytest.raises(RuntimeError) as exc_info:
        await agent._sandbox_exec(
            task_id=task_id,
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    assert route.call_count == 3
    assert "HTTP 500" in str(exc_info.value)
    assert "Error happened when allocating pod" in str(exc_info.value)
    stderr_entries = _stderr_entries(task_id)
    assert len(stderr_entries) == 1
    assert "Error happened when allocating pod" in stderr_entries[0]["data"]


@pytest.mark.asyncio
@respx.mock
async def test_http_400_missing_token_does_not_retry(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pool returns 400 missing token → fail immediately without retry."""
    route = respx.post(f"{ENDPOINT}/tasks").mock(
        return_value=httpx.Response(400, text="missing token")
    )
    monkeypatch.setattr(agent, "_sandbox_client", _RespxSandboxClient)

    task_id = "task-400-no-retry"
    _pipeline_outputs[task_id] = []

    with pytest.raises(RuntimeError) as exc_info:
        await agent._sandbox_exec(
            task_id=task_id,
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    assert route.call_count == 1
    assert "HTTP 400" in str(exc_info.value)
    assert "missing token" in str(exc_info.value)
    assert len(_stderr_entries(task_id)) == 1


@pytest.mark.asyncio
@respx.mock
async def test_connect_error_twice_then_success_succeeds(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transport ConnectError twice, then 200 → succeeds."""
    route = respx.post(f"{ENDPOINT}/tasks").mock(
        side_effect=[
            httpx.ConnectError("connection refused"),
            httpx.ConnectError("connection refused"),
            httpx.Response(200, json={"id": "sandbox-task-ok"}),
        ]
    )
    monkeypatch.setattr(agent, "_sandbox_client", _RespxSandboxClient)

    task_id = "task-connect-retry"
    _pipeline_outputs[task_id] = []

    output = await agent._sandbox_exec(
        task_id=task_id,
        command="echo hello",
        args=[],
        stage_label="implement",
    )

    assert output == "ok\n"
    assert route.call_count == 3
    assert _stderr_entries(task_id) == []
