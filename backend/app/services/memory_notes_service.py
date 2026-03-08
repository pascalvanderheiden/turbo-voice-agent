"""In-memory notes service — drop-in replacement for NotesService when Cosmos DB is unavailable."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.note import Note, NoteCreate, NoteUpdate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class InMemoryNotesService(JsonPersistenceMixin):
    """In-memory CRUD for notes with JSON file persistence."""


    _json_file = "notes.json"

    def __init__(self, user_id: str = DEFAULT_USER_ID):
        self._user_id = user_id
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def with_user(self, user_id: str):
        """No-op: in-memory service does not scope by user."""
        return self

    def _doc_to_model(self, doc: dict) -> Note:
        return Note(
            id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            images=doc.get("images", []),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: NoteCreate) -> Note | None:
        now = datetime.now(UTC)
        note_id = str(uuid.uuid4())
        doc = {
            "id": note_id,
            "userId": self._user_id,
            "title": data.title,
            "content": data.content,
            "images": data.images,
            "docType": "note",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[note_id] = doc
        self._save_to_disk()
        logger.info("Created note %s (in-memory)", note_id)
        return self._doc_to_model(doc)

    async def list(self) -> list[Note]:
        docs = sorted(self._store.values(), key=lambda d: d["updatedAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, note_id: str) -> Note | None:
        doc = self._store.get(note_id)
        return self._doc_to_model(doc) if doc else None

    async def update(self, note_id: str, data: NoteUpdate) -> Note | None:
        doc = self._store.get(note_id)
        if not doc:
            return None
        if data.title is not None:
            doc["title"] = data.title
        if data.content is not None:
            doc["content"] = data.content
        if data.images is not None:
            doc["images"] = data.images
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        logger.info("Updated note %s (in-memory)", note_id)
        return self._doc_to_model(doc)

    async def delete(self, note_id: str) -> bool:
        if note_id in self._store:
            del self._store[note_id]
            self._save_to_disk()
            logger.info("Deleted note %s (in-memory)", note_id)
            return True
        return False
