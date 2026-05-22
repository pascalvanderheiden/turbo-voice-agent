"""Tests for the GitHub-sandbox disconnect endpoint (Phase 6 of sandbox-dynamic-sessions).

Verifies that ``DELETE /api/me/connections/github-sandbox``:
- Enumerates the calling user's active dev-tasks.
- Calls ``SandboxClient.stop_session(task_id)`` once per active task.
- Clears the stored PAT.
- Reports the number of released sessions in the response body.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.routes import user as user_routes


@pytest.fixture(autouse=True)
def _reset_connection_store() -> None:
    user_routes._connection_store.clear()
    yield
    user_routes._connection_store.clear()


def _make_request(
    *,
    user_id: str,
    dev_service: MagicMock | None,
    profile_service: MagicMock | None,
) -> SimpleNamespace:
    """Build a minimal stand-in for a FastAPI ``Request`` object."""
    state = SimpleNamespace(user_id=user_id, user_claims={})
    app_state = SimpleNamespace(
        dev_service=dev_service,
        user_profile_service=profile_service,
    )
    return SimpleNamespace(state=state, app=SimpleNamespace(state=app_state))


@pytest.mark.asyncio
async def test_disconnect_stops_active_sessions_and_clears_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disconnect releases per-task sandbox sessions then clears the PAT."""
    # Two active dev-tasks and one stale "completed" one — only the active two
    # should trigger stop_session calls.
    tasks = [
        SimpleNamespace(id="task-1", status="running"),
        SimpleNamespace(id="task-2", status="provisioning"),
        SimpleNamespace(id="task-3", status="completed"),
    ]
    user_scoped = MagicMock()
    user_scoped.list = AsyncMock(return_value=tasks)
    dev_service = MagicMock()
    dev_service.with_user = MagicMock(return_value=user_scoped)

    profile_service = MagicMock()
    profile_service.update_sandbox_token = AsyncMock(return_value=None)

    stop_calls: list[str] = []

    async def _stop_session(task_id: str) -> None:
        stop_calls.append(task_id)

    stub_client = MagicMock()
    stub_client.stop_session = AsyncMock(side_effect=_stop_session)
    monkeypatch.setattr(
        "app.services.session_sandbox_client.get_sandbox_client",
        lambda: stub_client,
    )

    # Pretend the user had a stored PAT so the clear-side is exercised.
    user_routes._connection_store["sandbox:user-x"] = {
        "token": "encrypted-blob",
        "connectedAt": "2025-01-01T00:00:00+00:00",
    }

    req = _make_request(
        user_id="user-x",
        dev_service=dev_service,
        profile_service=profile_service,
    )

    resp = await user_routes.disconnect_sandbox(req)

    # JSONResponse path vs dict return path — handler returns dict.
    assert resp == {"connected": False, "stoppedSessions": 2}
    assert sorted(stop_calls) == ["task-1", "task-2"]
    # In-memory store cleared.
    assert "sandbox:user-x" not in user_routes._connection_store
    # Cosmos profile cleared.
    profile_service.update_sandbox_token.assert_awaited_once_with("user-x", None, None)


@pytest.mark.asyncio
async def test_disconnect_with_no_active_tasks_still_clears_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disconnect with zero active tasks is a no-op for sessions, but still clears the PAT."""
    user_scoped = MagicMock()
    user_scoped.list = AsyncMock(return_value=[])
    dev_service = MagicMock()
    dev_service.with_user = MagicMock(return_value=user_scoped)

    profile_service = MagicMock()
    profile_service.update_sandbox_token = AsyncMock(return_value=None)

    stub_client = MagicMock()
    stub_client.stop_session = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.services.session_sandbox_client.get_sandbox_client",
        lambda: stub_client,
    )

    user_routes._connection_store["sandbox:user-empty"] = {"token": "x"}
    req = _make_request(
        user_id="user-empty",
        dev_service=dev_service,
        profile_service=profile_service,
    )

    resp = await user_routes.disconnect_sandbox(req)

    assert resp == {"connected": False, "stoppedSessions": 0}
    stub_client.stop_session.assert_not_awaited()
    assert "sandbox:user-empty" not in user_routes._connection_store


@pytest.mark.asyncio
async def test_disconnect_unauthenticated_returns_401() -> None:
    req = _make_request(user_id=None, dev_service=None, profile_service=None)
    resp = await user_routes.disconnect_sandbox(req)
    # JSONResponse object
    assert getattr(resp, "status_code", None) == 401
