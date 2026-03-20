"""Tests for SlidesAgent handle_function_call routing."""

import json

import pytest

from app.agents.slides_agent import SlidesAgent
from app.services.memory_slides_service import InMemorySlidesService


@pytest.fixture
def service(tmp_path):
    svc = InMemorySlidesService()
    svc._json_file = str(tmp_path / "slides.json")
    return svc


@pytest.fixture
def agent(service):
    return SlidesAgent(slides_service=service)


@pytest.mark.asyncio
async def test_create_slides(agent):
    result = await agent.handle_function_call(
        "create_slides", json.dumps({"title": "My Deck", "description": "About AI"})
    )
    data = json.loads(result)
    assert data["success"] is True
    assert data["slides"]["title"] == "My Deck"
    assert "id" in data["slides"]


@pytest.mark.asyncio
async def test_list_slides(agent):
    await agent.handle_function_call(
        "create_slides", json.dumps({"title": "Deck A"})
    )
    await agent.handle_function_call(
        "create_slides", json.dumps({"title": "Deck B"})
    )
    result = await agent.handle_function_call("get_slides_list", "{}")
    data = json.loads(result)
    assert len(data["slides"]) == 2
    titles = {s["title"] for s in data["slides"]}
    assert titles == {"Deck A", "Deck B"}


@pytest.mark.asyncio
async def test_get_slides(agent):
    create_res = json.loads(
        await agent.handle_function_call(
            "create_slides", json.dumps({"title": "Test"})
        )
    )
    slides_id = create_res["slides"]["id"]

    result = await agent.handle_function_call(
        "get_slides", json.dumps({"slides_id": slides_id})
    )
    data = json.loads(result)
    assert data["slides"]["id"] == slides_id
    assert data["slides"]["title"] == "Test"


@pytest.mark.asyncio
async def test_get_slides_not_found(agent):
    result = await agent.handle_function_call(
        "get_slides", json.dumps({"slides_id": "nonexistent"})
    )
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_update_slides(agent):
    create_res = json.loads(
        await agent.handle_function_call(
            "create_slides", json.dumps({"title": "Original"})
        )
    )
    slides_id = create_res["slides"]["id"]

    result = await agent.handle_function_call(
        "update_slides",
        json.dumps({"slides_id": slides_id, "title": "Updated Title"}),
    )
    data = json.loads(result)
    assert data["success"] is True
    assert data["slides"]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_slides(agent):
    create_res = json.loads(
        await agent.handle_function_call(
            "create_slides", json.dumps({"title": "ToDelete"})
        )
    )
    slides_id = create_res["slides"]["id"]

    result = await agent.handle_function_call(
        "delete_slides", json.dumps({"slides_id": slides_id})
    )
    data = json.loads(result)
    assert data["success"] is True

    # Verify it's gone
    get_result = await agent.handle_function_call(
        "get_slides", json.dumps({"slides_id": slides_id})
    )
    assert "error" in json.loads(get_result)


@pytest.mark.asyncio
async def test_unknown_function(agent):
    result = await agent.handle_function_call("nonexistent_func", "{}")
    data = json.loads(result)
    assert "error" in data
    assert "Unknown function" in data["error"]


@pytest.mark.asyncio
async def test_invalid_arguments(agent):
    result = await agent.handle_function_call("create_slides", "not-json")
    data = json.loads(result)
    assert "error" in data
