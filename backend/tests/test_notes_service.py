"""Tests for NotesService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.note import NoteCreate, NoteUpdate
from app.services.notes_service import NotesService


@pytest.fixture
def mock_container():
    container = AsyncMock()
    return container


@pytest.fixture
def mock_client(mock_container):
    client = MagicMock()
    db = MagicMock()
    db.get_container_client.return_value = mock_container
    client.get_database_client.return_value = db
    return client


@pytest.fixture
def service(mock_client):
    return NotesService(mock_client, user_id="test-user")


def _make_doc(note_id: str = "test-id", title: str = "Test", content: str = "Content") -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "id": note_id,
        "userId": "test-user",
        "title": title,
        "content": content,
        "docType": "note",
        "createdAt": now,
        "updatedAt": now,
    }


@pytest.mark.asyncio
async def test_create_note(service, mock_container):
    doc = _make_doc()
    mock_container.upsert_item.return_value = doc

    result = await service.create(NoteCreate(title="Test", content="Content"))

    assert result is not None
    assert result.title == "Test"
    mock_container.upsert_item.assert_called_once()


@pytest.mark.asyncio
async def test_list_notes(service, mock_container):
    docs = [_make_doc("1", "First", "A"), _make_doc("2", "Second", "B")]

    async def mock_query(*args, **kwargs):
        for doc in docs:
            yield doc

    mock_container.query_items.return_value = mock_query()

    result = await service.list()

    assert len(result) == 2
    assert result[0].title == "First"


@pytest.mark.asyncio
async def test_get_by_id(service, mock_container):
    doc = _make_doc("abc")
    mock_container.read_item.return_value = doc

    result = await service.get_by_id("abc")

    assert result is not None
    assert result.id == "abc"
    mock_container.read_item.assert_called_once_with(item="abc", partition_key="test-user")


@pytest.mark.asyncio
async def test_get_by_id_not_found(service, mock_container):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    mock_container.read_item.side_effect = CosmosResourceNotFoundError(
        status_code=404, message="Not found"
    )

    result = await service.get_by_id("missing")
    assert result is None


@pytest.mark.asyncio
async def test_update_note(service, mock_container):
    doc = _make_doc("abc", "Old Title", "Old Content")
    mock_container.read_item.return_value = doc

    updated_doc = {**doc, "title": "New Title", "updatedAt": datetime.now(UTC).isoformat()}
    mock_container.replace_item.return_value = updated_doc

    result = await service.update("abc", NoteUpdate(title="New Title"))

    assert result is not None
    assert result.title == "New Title"


@pytest.mark.asyncio
async def test_delete_note(service, mock_container):
    mock_container.delete_item.return_value = None

    result = await service.delete("abc")
    assert result is True


@pytest.mark.asyncio
async def test_delete_note_not_found(service, mock_container):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    mock_container.delete_item.side_effect = CosmosResourceNotFoundError(
        status_code=404, message="Not found"
    )

    result = await service.delete("missing")
    assert result is False


@pytest.mark.asyncio
async def test_create_note_failure(service, mock_container):
    mock_container.upsert_item.side_effect = Exception("Connection failed")

    result = await service.create(NoteCreate(title="Test", content="Content"))
    assert result is None
