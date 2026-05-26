"""Tests for /api/sandbox/recreate releasing user sessions (Fix 4)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.dev_task import DevTask
from app.routes import sandbox


@pytest.mark.asyncio
async def test_recreate_stops_active_user_sessions():
    """Recreate enumerates user's active tasks and calls stop_session for each."""

    # Mock dev service with 3 tasks: 2 active, 1 completed
    mock_dev_service = MagicMock()
    mock_user_dev_service = MagicMock()
    mock_dev_service.with_user = MagicMock(return_value=mock_user_dev_service)

    task1 = DevTask(
        id="task-running",
        userId="test-user",
        title="Task 1",
        status="running",
        mode="mockup",
        iterations=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    task2 = DevTask(
        id="task-provisioning",
        userId="test-user",
        title="Task 2",
        status="provisioning",
        mode="mockup",
        iterations=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    task3 = DevTask(
        id="task-completed",
        userId="test-user",
        title="Task 3",
        status="completed",
        mode="mockup",
        iterations=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )

    mock_user_dev_service.list = AsyncMock(return_value=[task1, task2, task3])

    # Mock sandbox service
    mock_sandbox_service = MagicMock()
    mock_sandbox_service.with_user = MagicMock(return_value=mock_sandbox_service)
    mock_sandbox_service.set_status = AsyncMock()
    sandbox.set_sandbox_service(mock_sandbox_service)

    # Mock sandbox client
    mock_client = MagicMock()
    mock_client.stop_session = AsyncMock()

    # Mock request
    class MockState:
        user_id = "test-user"

    class MockApp:
        class State:
            dev_service = mock_dev_service

        state = State()

    class MockRequest:
        state = MockState()
        app = MockApp()

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        result = await sandbox.recreate_sandbox(MockRequest())

    # Verify only active tasks were stopped (2 out of 3)
    assert mock_client.stop_session.call_count == 2
    stopped_task_ids = [call[0][0] for call in mock_client.stop_session.call_args_list]
    assert "task-running" in stopped_task_ids
    assert "task-provisioning" in stopped_task_ids
    assert "task-completed" not in stopped_task_ids

    # Verify response
    assert result["status"] == "ready"
    assert len(result["stopped"]) == 2
    assert "Released 2 session(s)" in result["message"]


@pytest.mark.asyncio
async def test_recreate_handles_no_active_tasks():
    """Recreate with no active tasks returns appropriate message."""

    mock_dev_service = MagicMock()
    mock_user_dev_service = MagicMock()
    mock_dev_service.with_user = MagicMock(return_value=mock_user_dev_service)
    mock_user_dev_service.list = AsyncMock(return_value=[])

    mock_sandbox_service = MagicMock()
    mock_sandbox_service.with_user = MagicMock(return_value=mock_sandbox_service)
    mock_sandbox_service.set_status = AsyncMock()
    sandbox.set_sandbox_service(mock_sandbox_service)

    mock_client = MagicMock()
    mock_client.stop_session = AsyncMock()

    class MockState:
        user_id = "test-user"

    class MockApp:
        class State:
            dev_service = mock_dev_service

        state = State()

    class MockRequest:
        state = MockState()
        app = MockApp()

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        result = await sandbox.recreate_sandbox(MockRequest())

    assert mock_client.stop_session.call_count == 0
    assert result["status"] == "ready"
    assert len(result["stopped"]) == 0
    assert "No active sessions" in result["message"]


@pytest.mark.asyncio
async def test_recreate_continues_on_stop_failure():
    """Recreate logs errors but continues processing remaining tasks."""

    mock_dev_service = MagicMock()
    mock_user_dev_service = MagicMock()
    mock_dev_service.with_user = MagicMock(return_value=mock_user_dev_service)

    task1 = DevTask(
        id="task-1",
        userId="test-user",
        title="Task 1",
        status="running",
        mode="mockup",
        iterations=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    task2 = DevTask(
        id="task-2",
        userId="test-user",
        title="Task 2",
        status="running",
        mode="mockup",
        iterations=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )

    mock_user_dev_service.list = AsyncMock(return_value=[task1, task2])

    mock_sandbox_service = MagicMock()
    mock_sandbox_service.with_user = MagicMock(return_value=mock_sandbox_service)
    mock_sandbox_service.set_status = AsyncMock()
    sandbox.set_sandbox_service(mock_sandbox_service)

    # First call fails, second succeeds
    mock_client = MagicMock()
    mock_client.stop_session = AsyncMock(side_effect=[Exception("Session not found"), None])

    class MockState:
        user_id = "test-user"

    class MockApp:
        class State:
            dev_service = mock_dev_service

        state = State()

    class MockRequest:
        state = MockState()
        app = MockApp()

    with patch("app.routes.sandbox.get_sandbox_client", return_value=mock_client):
        result = await sandbox.recreate_sandbox(MockRequest())

    # Both stop_session calls attempted
    assert mock_client.stop_session.call_count == 2
    # Only one succeeded
    assert len(result["stopped"]) == 1
    assert "task-2" in result["stopped"]
