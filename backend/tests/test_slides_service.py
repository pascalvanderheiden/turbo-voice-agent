"""Tests for slides in-memory service and archive functionality."""

import pytest

from app.models.slides import SlidesCreate, SlidesUpdate
from app.services.memory_slides_service import InMemorySlidesService
from app.models.dev_task import DevTaskCreate
from app.services.dev_service import InMemoryDevService


@pytest.fixture
def slides_service(tmp_path):
    svc = InMemorySlidesService()
    svc._json_file = str(tmp_path / "slides.json")
    return svc.with_user("test-user")


@pytest.fixture
def dev_service(tmp_path):
    svc = InMemoryDevService()
    svc._json_file = str(tmp_path / "dev_tasks.json")
    return svc.with_user("test-user")


@pytest.mark.asyncio
async def test_create_and_list_slides(slides_service):
    result = await slides_service.create(SlidesCreate(title="Test Deck", description="A test"))
    assert result.id
    assert result.title == "Test Deck"
    items = await slides_service.list()
    assert len(items) == 1


@pytest.mark.asyncio
async def test_get_update_delete_slides(slides_service):
    created = await slides_service.create(SlidesCreate(title="Deck"))
    fetched = await slides_service.get_by_id(created.id)
    assert fetched.title == "Deck"

    updated = await slides_service.update(created.id, SlidesUpdate(title="Updated Deck"))
    assert updated.title == "Updated Deck"

    deleted = await slides_service.delete(created.id)
    assert deleted is True
    assert await slides_service.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_slides_dev_task_has_correct_stages(dev_service):
    task = await dev_service.create(
        DevTaskCreate(title="Slide Task", mode="slides", slidesId="s1")
    )
    assert task.mode == "slides"
    assert task.slides_id == "s1"
    # Slides mode should have 3 stages: init, slides, export
    assert len(task.iterations) == 1
    stage_names = [s.name for s in task.iterations[0].stages]
    assert stage_names == ["init", "slides", "export"]


@pytest.mark.asyncio
async def test_dev_task_archive(dev_service):
    task = await dev_service.create(DevTaskCreate(title="Archivable"))
    assert task.archived is False

    await dev_service.set_archived(task.id, True)
    updated = await dev_service.get_by_id(task.id)
    assert updated.archived is True

    await dev_service.set_archived(task.id, False)
    updated = await dev_service.get_by_id(task.id)
    assert updated.archived is False


@pytest.mark.asyncio
async def test_default_dev_task_has_mockup_stages(dev_service):
    task = await dev_service.create(DevTaskCreate(title="Regular"))
    stage_names = [s.name for s in task.iterations[0].stages]
    assert "init" in stage_names
    assert "skills" in stage_names
    assert "implement" in stage_names
    assert "screenshots" in stage_names
