"""Tests for Phase 6 of sandbox-dynamic-sessions: X-GH-Token header flow.

Covers:
- First sandbox call (skills-sync) attaches ``X-GH-Token``.
- Subsequent calls (_sandbox_exec, more skills-syncs) for the same task do NOT
  resend the header (the sandbox container retains gh-auth state for session lifetime).
- ``cancel_sandbox_task_for`` and ``_teardown_sandbox_session`` clear the
  per-task tracker so re-runs receive a fresh bootstrap.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.agents import dev_agent as dev_agent_mod
from app.agents.dev_agent import DevAgent, _gh_token_sent, cancel_sandbox_task_for


class _StopRequest(Exception):
    """Sentinel raised by mock to short-circuit ``_sandbox_exec`` post-POST."""


def _make_mock_client(recorder: list[dict[str, Any]]) -> MagicMock:
    """Return a mock SandboxClient whose ``request`` records call kwargs and aborts."""

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        recorder.append({"method": method, "path": path, "kwargs": kwargs})
        raise _StopRequest()

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    client.stop_session = AsyncMock(return_value=None)
    return client


@pytest.fixture(autouse=True)
def _clear_tracker() -> None:
    """Ensure each test starts with an empty token-sent tracker."""
    _gh_token_sent.clear()
    yield
    _gh_token_sent.clear()


@pytest.fixture
def agent() -> DevAgent:
    return DevAgent(dev_service=MagicMock())


@pytest.mark.asyncio
async def test_skills_sync_attaches_x_gh_token_first(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skills-sync is the FIRST sandbox call; it attaches X-GH-Token."""
    recorder: list[dict[str, Any]] = []

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        recorder.append({"method": method, "path": path, "kwargs": kwargs})
        # Return successful skills-sync response
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"synced": 0, "skills": []}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)
    agent._current_gh_token = "ghp_test_skills_sync_123"

    await agent._sync_skills_stage(task_id="task-sync-first")

    assert len(recorder) == 1
    assert recorder[0]["path"] == "/skills/sync"
    headers = recorder[0]["kwargs"].get("headers")
    assert headers is not None, "skills-sync must attach headers dict"
    assert headers.get("X-GH-Token") == "ghp_test_skills_sync_123"
    assert "task-sync-first" in _gh_token_sent


@pytest.mark.asyncio
async def test_sandbox_exec_after_skills_sync_omits_token(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_sandbox_exec called AFTER skills-sync sees task already in _gh_token_sent, omits header."""
    recorder: list[dict[str, Any]] = []
    client = _make_mock_client(recorder)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)
    agent._current_gh_token = "ghp_test_pat_456"

    # Simulate skills-sync already ran and added task to tracker
    _gh_token_sent.add("task-after-sync")

    with pytest.raises(_StopRequest):
        await agent._sandbox_exec(
            task_id="task-after-sync",
            command="echo hello",
            args=[],
            stage_label="implement",
        )

    assert len(recorder) == 1
    headers = recorder[0]["kwargs"].get("headers")
    # Header dict may exist but must NOT contain X-GH-Token
    if headers is not None:
        assert "X-GH-Token" not in headers


@pytest.mark.asyncio
async def test_first_call_attaches_x_gh_token(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First sandbox call for a dev-task carries the user's PAT as ``X-GH-Token``."""
    recorder: list[dict[str, Any]] = []
    client = _make_mock_client(recorder)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)
    agent._current_gh_token = "ghp_test_pat_123"

    with pytest.raises(_StopRequest):
        await agent._sandbox_exec(
            task_id="task-abc",
            command="echo hello",
            args=[],
            stage_label="cleanup",
        )

    assert len(recorder) == 1
    headers = recorder[0]["kwargs"].get("headers")
    assert headers is not None, "first call must attach headers dict"
    assert headers.get("X-GH-Token") == "ghp_test_pat_123"
    assert "task-abc" in _gh_token_sent


@pytest.mark.asyncio
async def test_second_call_omits_x_gh_token(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subsequent call for the same dev-task does NOT resend the PAT."""
    recorder: list[dict[str, Any]] = []
    client = _make_mock_client(recorder)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)
    agent._current_gh_token = "ghp_test_pat_123"

    # First call — bootstraps and records the task in _gh_token_sent.
    with pytest.raises(_StopRequest):
        await agent._sandbox_exec(
            task_id="task-abc",
            command="echo first",
            args=[],
            stage_label="cleanup",
        )

    # Second call — same task; header must be omitted (or None).
    with pytest.raises(_StopRequest):
        await agent._sandbox_exec(
            task_id="task-abc",
            command="echo second",
            args=[],
            stage_label="impl",
        )

    assert len(recorder) == 2
    second_headers = recorder[1]["kwargs"].get("headers")
    # Either headers is None or it does not contain the X-GH-Token key.
    if second_headers is not None:
        assert "X-GH-Token" not in second_headers


@pytest.mark.asyncio
async def test_no_token_means_no_header(agent: DevAgent, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the user has no PAT, no ``X-GH-Token`` header is attached."""
    recorder: list[dict[str, Any]] = []
    client = _make_mock_client(recorder)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)
    agent._current_gh_token = None

    with pytest.raises(_StopRequest):
        await agent._sandbox_exec(
            task_id="task-no-pat",
            command="echo",
            args=[],
            stage_label="cleanup",
        )

    headers = recorder[0]["kwargs"].get("headers")
    if headers is not None:
        assert "X-GH-Token" not in headers
    assert "task-no-pat" not in _gh_token_sent


@pytest.mark.asyncio
async def test_cancel_clears_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    """``cancel_sandbox_task_for`` removes the task from ``_gh_token_sent``."""
    _gh_token_sent.add("task-cancel")

    # Stub out the sandbox client so cancel doesn't touch any real network.
    stub_client = MagicMock()
    stub_client.request = AsyncMock(return_value=MagicMock(status_code=200))
    stub_client.stop_session = AsyncMock(return_value=None)
    monkeypatch.setattr(dev_agent_mod, "get_sandbox_client", lambda: stub_client)
    # Simulate that an active sandbox sub-task exists so the DELETE path runs.
    dev_agent_mod._active_sandbox_tasks["task-cancel"] = "sandbox-1"

    await cancel_sandbox_task_for("task-cancel")

    assert "task-cancel" not in _gh_token_sent


@pytest.mark.asyncio
async def test_teardown_clears_tracker(agent: DevAgent, monkeypatch: pytest.MonkeyPatch) -> None:
    """``_teardown_sandbox_session`` removes the task from ``_gh_token_sent``."""
    _gh_token_sent.add("task-teardown")
    stub_client = MagicMock()
    stub_client.stop_session = AsyncMock(return_value=None)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: stub_client)

    await agent._teardown_sandbox_session("task-teardown")

    assert "task-teardown" not in _gh_token_sent
    stub_client.stop_session.assert_awaited_once_with("task-teardown")
