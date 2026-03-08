"""Notes REST API routes."""

from fastapi import APIRouter, HTTPException, Request

from app.models.note import Note, NoteCreate, NoteUpdate
from app.services.notes_service import NotesService

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Injected at startup via app state
_notes_service: NotesService | None = None


def set_notes_service(service: NotesService) -> None:
    global _notes_service
    _notes_service = service


def _get_service() -> NotesService:
    if _notes_service is None:
        raise HTTPException(status_code=503, detail="Notes service unavailable")
    return _notes_service


@router.get("", response_model=list[Note])
async def list_notes(request: Request):
    """List all notes."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    return await service.list()


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str, request: Request):
    """Get a single note by ID."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    note = await service.get_by_id(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("", response_model=Note, status_code=201)
async def create_note(data: NoteCreate, request: Request):
    """Create a new note."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    note = await service.create(data)
    if note is None:
        raise HTTPException(status_code=500, detail="Failed to create note")
    return note


@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, data: NoteUpdate, request: Request):
    """Update an existing note."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    note = await service.update(note_id, data)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: str, request: Request):
    """Delete a note."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    deleted = await service.delete(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
