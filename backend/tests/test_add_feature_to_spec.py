"""Tests for the add_feature_to_spec pipeline — spec agent feature enhancement and integration."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.spec_agent import SpecAgent, ENHANCE_FEATURE_SYSTEM_PROMPT
from app.services.memory_spec_service import InMemorySpecService


@pytest.fixture
def spec_service():
    svc = InMemorySpecService()
    svc._store = {}
    return svc


@pytest.fixture
def dev_agent_mock():
    mock = AsyncMock()
    mock.append_feature_iteration = AsyncMock(return_value={
        "extended": True,
        "pipeline_triggered": True,
        "iteration_index": 2,
    })
    return mock


@pytest.fixture
def agent(spec_service, dev_agent_mock):
    return SpecAgent(spec_service, dev_agent=dev_agent_mock)


SAMPLE_SPEC_CONTENT = """## Mockup Description

A modern dashboard app with dark theme featuring a sidebar navigation,
metric cards grid, and data table. Primary color is cyan.

## OpenSpec Config

### Foundation
Build a Next.js 15 app with sidebar layout and dark theme.

### Features
#### Feature: User Dashboard
Create a dashboard with metric cards showing real-time data.

#### Feature: Data Table
Implement a sortable, filterable data table component.
"""


async def _create_foundation_spec(service, content=SAMPLE_SPEC_CONTENT, dev_task_id=None):
    """Helper to create a foundation spec in the service."""
    from app.models.spec import SpecCreate
    spec = await service.create(SpecCreate(title="Test App", content=content, type="foundation"))
    if dev_task_id and hasattr(spec, 'devTaskId'):
        await service.set_dev_task_id(spec.id, dev_task_id, "in-development")
    return spec


class TestEnhanceFeature:
    """Tests for SpecAgent.enhance_feature()."""

    @pytest.mark.asyncio
    async def test_enhance_feature_returns_three_parts(self, agent):
        """enhance_feature returns (feature_name, mockup_paragraph, propose_instruction)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "## Mockup Addition\n\n"
            "A dark mode toggle in the top bar allows switching between light and dark themes "
            "with smooth transitions. The preference is persisted across sessions.\n\n"
            "## Feature Entry\n\n"
            "#### Feature: Dark Mode\n"
            "Add a dark mode toggle to the top navigation bar with system preference detection "
            "and localStorage persistence. Support smooth CSS transitions between themes."
        )

        with patch.object(agent, '_get_openai') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            name, mockup, instruction = await agent.enhance_feature(
                SAMPLE_SPEC_CONTENT, "dark mode support"
            )

        assert name == "Dark Mode"
        assert "dark mode toggle" in mockup.lower()
        assert "dark mode toggle" in instruction.lower()
        assert len(mockup.split()) >= 10  # At least 10 words

    @pytest.mark.asyncio
    async def test_enhance_feature_includes_existing_spec_context(self, agent):
        """The GPT-5.2 call includes existing spec content for coherence."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "## Mockup Addition\n\nSome mockup.\n\n"
            "## Feature Entry\n\n#### Feature: Test\nSome instruction."
        )

        with patch.object(agent, '_get_openai') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            await agent.enhance_feature(SAMPLE_SPEC_CONTENT, "test feature")

            # Verify the call included existing spec content
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs.get("messages", call_args[1].get("messages", []))
            user_msg = messages[-1]["content"]
            assert "dashboard app" in user_msg  # existing spec content
            assert "test feature" in user_msg  # new feature description

    @pytest.mark.asyncio
    async def test_enhance_feature_fallback_on_missing_sections(self, agent):
        """Falls back gracefully when GPT output is missing expected sections."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Just some text without proper formatting"

        with patch.object(agent, '_get_openai') as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            name, mockup, instruction = await agent.enhance_feature(
                SAMPLE_SPEC_CONTENT, "dark mode support"
            )

        # Should fall back to raw description
        assert name  # Should have some name (truncated description)
        assert instruction  # Should have some instruction


class TestAddFeatureToSpec:
    """Tests for SpecAgent.add_feature_to_spec()."""

    @pytest.mark.asyncio
    async def test_add_feature_updates_spec_content(self, agent, spec_service):
        """Adding a feature appends to the spec's Mockup Description and OpenSpec Config."""
        spec = await _create_foundation_spec(spec_service)

        with patch.object(agent, 'enhance_feature', new_callable=AsyncMock) as mock_enhance:
            mock_enhance.return_value = (
                "Dark Mode",
                "A dark mode toggle in the top bar.",
                "Add dark mode with system preference detection.",
            )

            result = await agent.add_feature_to_spec(spec.id, "dark mode", user_id="test-user")

        assert result["success"] is True
        assert result["feature_name"] == "Dark Mode"

        # Verify spec content was updated
        updated = await spec_service.get_by_id(spec.id)
        assert "Dark Mode" in updated.content
        assert "dark mode toggle" in updated.content.lower()
        assert "#### Feature: Dark Mode" in updated.content

    @pytest.mark.asyncio
    async def test_add_feature_to_nonexistent_spec(self, agent):
        """Returns error for non-existent spec ID."""
        result = await agent.add_feature_to_spec("nonexistent", "dark mode")
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_add_feature_to_feature_type_spec(self, agent, spec_service):
        """Returns error when trying to add feature to a feature-type spec."""
        from app.models.spec import SpecCreate
        spec = await spec_service.create(
            SpecCreate(title="Some Feature", content="content", type="feature")
        )

        result = await agent.add_feature_to_spec(spec.id, "dark mode", user_id="test-user")
        assert "error" in result
        assert "foundation" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_add_feature_no_dev_task(self, agent, spec_service):
        """When spec has no linked dev task, only updates spec — no pipeline trigger."""
        spec = await _create_foundation_spec(spec_service)

        with patch.object(agent, 'enhance_feature', new_callable=AsyncMock) as mock_enhance:
            mock_enhance.return_value = ("Dark Mode", "Mockup text.", "Instruction text.")

            result = await agent.add_feature_to_spec(spec.id, "dark mode", user_id="test-user")

        assert result["success"] is True
        assert result["dev_task_extended"] is False
        assert result["pipeline_triggered"] is False


class TestAddFeatureHandleFunctionCall:
    """Tests for handle_function_call routing to add_feature_to_spec."""

    @pytest.mark.asyncio
    async def test_handle_function_call_routes_add_feature(self, agent, spec_service):
        """add_feature_to_spec function call is properly routed."""
        spec = await _create_foundation_spec(spec_service)

        with patch.object(agent, 'add_feature_to_spec', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = {
                "success": True,
                "feature_name": "Dark Mode",
                "spec_id": spec.id,
                "dev_task_extended": False,
                "pipeline_triggered": False,
            }

            result = await agent.handle_function_call(
                "add_feature_to_spec",
                json.dumps({"spec_id": spec.id, "description": "dark mode"}),
                user_id="test-user",
            )

        data = json.loads(result)
        assert data["success"] is True
        assert "Dark Mode" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_function_call_missing_params(self, agent):
        """Returns error when required parameters are missing."""
        result = await agent.handle_function_call(
            "add_feature_to_spec",
            json.dumps({"spec_id": "abc"}),
            user_id="test-user",
        )
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_handle_function_call_error_message(self, agent, spec_service):
        """Returns error from add_feature_to_spec when spec not found."""
        result = await agent.handle_function_call(
            "add_feature_to_spec",
            json.dumps({"spec_id": "nonexistent", "description": "dark mode"}),
            user_id="test-user",
        )
        data = json.loads(result)
        assert "error" in data
