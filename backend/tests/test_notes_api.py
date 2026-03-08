"""Tests for Notes REST API."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.note import Note
from app.routes.notes import set_notes_service
from app.services.notes_service import NotesService


@pytest.fixture
def mock_service():
    service = AsyncMock(spec=NotesService)
    set_notes_service(service)
    yield service
    set_notes_service(None)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _make_note(note_id: str = "test-id", title: str = "Test", content: str = "Content") -> Note:
    return Note(
        id=note_id,
        title=title,
        content=content,
        createdAt="2026-03-01T12:00:00Z",
        updatedAt="2026-03-01T12:00:00Z",
    )


def test_list_notes(client, mock_service):
    mock_service.list.return_value = [_make_note("1", "A", "B"), _make_note("2", "C", "D")]

    resp = client.get("/api/notes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_get_note(client, mock_service):
    mock_service.get_by_id.return_value = _make_note("abc")

    resp = client.get("/api/notes/abc")
    assert resp.status_code == 200
    assert resp.json()["id"] == "abc"


def test_get_note_not_found(client, mock_service):
    mock_service.get_by_id.return_value = None

    resp = client.get("/api/notes/missing")
    assert resp.status_code == 404


def test_create_note(client, mock_service):
    mock_service.create.return_value = _make_note("new")

    resp = client.post("/api/notes", json={"title": "New", "content": "Body"})
    assert resp.status_code == 201
    assert resp.json()["id"] == "new"


def test_update_note(client, mock_service):
    mock_service.update.return_value = _make_note("abc", "Updated", "Body")

    resp = client.put("/api/notes/abc", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


def test_update_note_not_found(client, mock_service):
    mock_service.update.return_value = None

    resp = client.put("/api/notes/missing", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_note(client, mock_service):
    mock_service.delete.return_value = True

    resp = client.delete("/api/notes/abc")
    assert resp.status_code == 204


def test_delete_note_not_found(client, mock_service):
    mock_service.delete.return_value = False

    resp = client.delete("/api/notes/missing")
    assert resp.status_code == 404
