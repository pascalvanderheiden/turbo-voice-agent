"""Tests for dev agent incremental feature pipeline — append_feature_iteration and pipeline execution."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.dev_agent import DevAgent
from app.services.dev_service import InMemoryDevService, _default_iteration
from app.models.dev_task import DevTaskCreate


@pytest.fixture
def dev_service():
    svc = InMemoryDevService()
    svc._store = {}
    return svc


@pytest.fixture
def agent(dev_service):
    return DevAgent(dev_service)


async def _create_openspec_task(service, with_foundation_complete=False):
    """Helper to create a sequential dev task with iterations."""
    task = await service.create(DevTaskCreate(title="Test App", specId="spec-1", mode="sequential"))

    # Add foundation and feature iterations
    iterations = [
        _default_iteration(0, "Foundation: Test App", "spec-1", mode="sequential"),
        _default_iteration(1, "Feature: Dashboard", "spec-1", mode="sequential"),
    ]
    await service.set_iterations(task.id, iterations)

    if with_foundation_complete:
        for stage_name in ["init", "implement-foundation"]:
            await service.set_iteration_stage_status(task.id, 0, stage_name, "completed")
        await service.set_status(task.id, "completed")

    return await service.get_by_id(task.id)


async def _create_mockup_task(service):
    """Helper to create a mockup dev task."""
    task = await service.create(DevTaskCreate(title="Mockup Test", specId="spec-1", mode="mockup"))
    return task


class TestAppendFeatureIteration:
    """Tests for DevAgent.append_feature_iteration()."""

    @pytest.mark.asyncio
    async def test_append_to_completed_foundation(self, agent, dev_service):
        """Appends iteration and triggers pipeline when foundation is complete."""
        task = await _create_openspec_task(dev_service, with_foundation_complete=True)

        with patch.object(agent, 'run_incremental_feature_pipeline', new_callable=AsyncMock):
            result = await agent.append_feature_iteration(
                task_id=task.id,
                feature_name="Dark Mode",
                propose_instruction="Add dark mode toggle.",
                spec_id="spec-1",
                user_id="test-user",
            )

        assert result["extended"] is True
        assert result["pipeline_triggered"] is True
        assert "iteration_index" in result

        # Verify iteration was added
        updated = await dev_service.get_by_id(task.id)
        assert len(updated.iterations) == 3  # foundation + dashboard + dark mode
        new_iter = updated.iterations[-1]
        assert "Dark Mode" in new_iter.label

    @pytest.mark.asyncio
    async def test_append_queued_when_foundation_pending(self, agent, dev_service):
        """Sets iteration to queued when foundation is not complete."""
        task = await _create_openspec_task(dev_service, with_foundation_complete=False)

        result = await agent.append_feature_iteration(
            task_id=task.id,
            feature_name="Dark Mode",
            propose_instruction="Add dark mode toggle.",
            spec_id="spec-1",
            user_id="test-user",
        )

        assert result["extended"] is True
        assert result["pipeline_triggered"] is False

    @pytest.mark.asyncio
    async def test_append_rejects_mockup_mode(self, agent, dev_service):
        """Rejects feature append for mockup mode tasks."""
        task = await _create_mockup_task(dev_service)

        result = await agent.append_feature_iteration(
            task_id=task.id,
            feature_name="Dark Mode",
            propose_instruction="Add dark mode.",
            spec_id="spec-1",
            user_id="test-user",
        )

        assert result["extended"] is False
        assert "sequential" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_append_to_nonexistent_task(self, agent):
        """Returns error for non-existent task ID."""
        result = await agent.append_feature_iteration(
            task_id="nonexistent",
            feature_name="Dark Mode",
            propose_instruction="Add dark mode.",
            spec_id="spec-1",
            user_id="test-user",
        )

        assert result["extended"] is False
        assert "not found" in result["error"].lower()


class TestDevServiceAddIteration:
    """Tests for InMemoryDevService.add_iteration()."""

    @pytest.mark.asyncio
    async def test_add_iteration_returns_new_index(self, dev_service):
        """add_iteration returns the correct new iteration index."""
        task = await _create_openspec_task(dev_service)

        new_iteration = _default_iteration(0, "Feature: New", "spec-1")
        new_idx = await dev_service.add_iteration(task.id, new_iteration)

        assert new_idx == 2  # 0=foundation, 1=dashboard, 2=new

    @pytest.mark.asyncio
    async def test_add_iteration_to_nonexistent_task(self, dev_service):
        """Returns None for non-existent task."""
        result = await dev_service.add_iteration("nonexistent", {"label": "test"})
        assert result is None


class TestSupervisorRouting:
    """Tests for supervisor routing of add_feature_to_spec."""

    @pytest.mark.asyncio
    async def test_supervisor_routes_add_feature_to_spec_agent(self):
        """Supervisor routes add_feature_to_spec to the Spec Agent."""
        from app.agents.supervisor import SupervisorAgent
        from app.agents.notes_agent import NotesAgent
        from app.services.memory_notes_service import InMemoryNotesService

        notes_agent = NotesAgent(InMemoryNotesService())
        spec_agent = MagicMock()
        spec_agent.tool_definitions = []
        spec_agent.handle_function_call = AsyncMock(return_value=json.dumps({"success": True}))

        supervisor = SupervisorAgent(notes_agent, spec_agent=spec_agent)

        result, agent_name = await supervisor.handle_function_call(
            "add_feature_to_spec",
            json.dumps({"spec_id": "abc", "description": "dark mode"}),
            user_id="test-user",
        )

        assert agent_name == "Spec Agent"
        spec_agent.handle_function_call.assert_called_once()
