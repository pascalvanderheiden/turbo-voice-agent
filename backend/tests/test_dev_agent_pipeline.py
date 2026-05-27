"""Tests for mockup pipeline fail-fast and preview readiness hardening."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.agents import dev_agent as dev_agent_mod
from app.agents.dev_agent import DevAgent, _pipeline_outputs
from app.models.dev_task import DevTaskCreate
from app.services.dev_service import InMemoryDevService


class PipelineDevService(InMemoryDevService):
    """In-memory dev service with tenant helper used by DevAgent pipelines."""

    def with_user(self, user_id: str) -> PipelineDevService:
        return self


@pytest.fixture(autouse=True)
def _clear_output_buffers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(dev_agent_mod.asyncio, "sleep", _no_sleep)
    _pipeline_outputs.clear()
    yield
    _pipeline_outputs.clear()


@pytest.fixture
def dev_service() -> PipelineDevService:
    svc = PipelineDevService()
    svc._store = {}
    return svc


@pytest.fixture
def agent(dev_service: PipelineDevService, monkeypatch: pytest.MonkeyPatch) -> DevAgent:
    agent = DevAgent(dev_service=dev_service)
    monkeypatch.setattr(
        agent,
        "_get_spec_content",
        AsyncMock(
            return_value=(
                "## Mockup Description\n"
                "Build a polished dashboard mockup with navigation, cards, and charts."
            )
        ),
    )
    monkeypatch.setattr(agent, "_get_user_model", AsyncMock(return_value="claude-test"))
    monkeypatch.setattr(agent, "_run_squad_stage", AsyncMock(return_value=None))
    monkeypatch.setattr(agent, "_sync_skills_stage", AsyncMock(return_value=None))
    monkeypatch.setattr(agent, "_checkpoint", AsyncMock(return_value=None))
    monkeypatch.setattr(agent, "_deactivate_squad", AsyncMock(return_value=None))
    return agent


async def _create_mockup_task(service: PipelineDevService) -> str:
    task = await service.create(DevTaskCreate(title="Mockup Test", specId="spec-1", mode="mockup"))
    _pipeline_outputs[task.id] = []
    return task.id


def _stderr_text(task_id: str) -> str:
    return "".join(
        entry.get("data", "")
        for entry in _pipeline_outputs[task_id]
        if entry.get("type") == "stderr"
    )


@pytest.mark.asyncio
async def test_implement_failure_aborts_pipeline(
    agent: DevAgent, dev_service: PipelineDevService, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = await _create_mockup_task(dev_service)

    async def _sandbox_exec(**kwargs: Any) -> str:
        if kwargs.get("prompt"):
            raise RuntimeError("Sandbox pool rejected task (HTTP 400): GitHub token required")
        return "ok"

    start_server = AsyncMock(return_value=3000)
    monkeypatch.setattr(agent, "_sandbox_exec", AsyncMock(side_effect=_sandbox_exec))
    monkeypatch.setattr(agent, "_start_mockup_dev_server", start_server)

    with pytest.raises(RuntimeError, match="Implement stage failed"):
        await agent._run_mockup_pipeline(task_id, "user-1")

    task = await dev_service.get_by_id(task_id)
    assert task.status == "failed"
    assert next(s for s in task.iterations[0].stages if s.name == "implement").status == "failed"
    start_server.assert_not_called()
    assert "❌ Implement stage failed — pipeline aborted." in _stderr_text(task_id)
    assert "No mockup app was generated." in _stderr_text(task_id)


@pytest.mark.asyncio
async def test_init_failure_aborts_pipeline(
    agent: DevAgent, dev_service: PipelineDevService, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = await _create_mockup_task(dev_service)

    async def _sandbox_exec(**kwargs: Any) -> str:
        if kwargs.get("stage_label") == "init":
            raise RuntimeError("Sandbox task [init] failed with exit code 1")
        return "ok"

    start_server = AsyncMock(return_value=3000)
    monkeypatch.setattr(agent, "_sandbox_exec", AsyncMock(side_effect=_sandbox_exec))
    monkeypatch.setattr(agent, "_start_mockup_dev_server", start_server)

    with pytest.raises(RuntimeError, match="Init stage failed"):
        await agent._run_mockup_pipeline(task_id, "user-1")

    task = await dev_service.get_by_id(task_id)
    assert task.status == "failed"
    assert next(s for s in task.iterations[0].stages if s.name == "init").status == "failed"
    start_server.assert_not_called()
    assert "❌ Init stage failed — pipeline aborted." in _stderr_text(task_id)


@pytest.mark.asyncio
async def test_preview_readiness_rejects_4xx(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = "preview-404"
    _pipeline_outputs[task_id] = []

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        request = httpx.Request(method, f"https://sandbox.example{path}")
        if method == "POST":
            return httpx.Response(200, json={"id": "server-task"}, request=request)
        return httpx.Response(404, text="Cannot GET /", request=request)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

    with pytest.raises(RuntimeError, match="Preview server never returned 2xx"):
        await agent._start_mockup_dev_server(task_id, "/workspace/preview-404")

    assert "❌ Preview server never returned 2xx on localhost:3000" in _stderr_text(task_id)
    assert "Last status: 404" in _stderr_text(task_id)


@pytest.mark.asyncio
async def test_preview_readiness_accepts_2xx(
    agent: DevAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = "preview-200"
    _pipeline_outputs[task_id] = []

    async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        request = httpx.Request(method, f"https://sandbox.example{path}")
        if method == "POST":
            return httpx.Response(200, json={"id": "server-task"}, request=request)
        return httpx.Response(200, text="ok", request=request)

    client = MagicMock()
    client.request = AsyncMock(side_effect=_request)
    monkeypatch.setattr(agent, "_sandbox_client", lambda: client)

    port = await agent._start_mockup_dev_server(task_id, "/workspace/preview-200")

    assert port == 3000
    assert any(entry.get("type") == "preview" for entry in _pipeline_outputs[task_id])


@pytest.mark.asyncio
async def test_empty_mockup_desc_aborts_implement(
    agent: DevAgent, dev_service: PipelineDevService, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = await _create_mockup_task(dev_service)
    sandbox_exec = AsyncMock(return_value="ok")
    monkeypatch.setattr(agent, "_extract_mockup_description", MagicMock(return_value=""))
    monkeypatch.setattr(agent, "_sandbox_exec", sandbox_exec)
    monkeypatch.setattr(agent, "_start_mockup_dev_server", AsyncMock(return_value=3000))

    with pytest.raises(RuntimeError, match="Spec produced no usable mockup description"):
        await agent._run_mockup_pipeline(task_id, "user-1")

    task = await dev_service.get_by_id(task_id)
    assert task.status == "failed"
    assert next(s for s in task.iterations[0].stages if s.name == "implement").status == "failed"
    assert not any(call.kwargs.get("prompt") for call in sandbox_exec.call_args_list)
    assert "spec_id=spec-1, desc_len=0" in _stderr_text(task_id)
