"""In-memory brainstorm service — same pattern as InMemoryNotesService."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.idea import Idea, IdeaCreate, IdeaUpdate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)


class InMemoryBrainstormService(JsonPersistenceMixin):
    """In-memory CRUD for ideas with JSON file persistence."""


    _json_file = "ideas.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def _doc_to_model(self, doc: dict) -> Idea:
        return Idea(
            id=doc["id"],
            title=doc["title"],
            description=doc.get("description", ""),
            images=doc.get("images", []),
            attachments=doc.get("attachments", []),
            status=doc.get("status", "draft"),
            refinedDraft=doc.get("refinedDraft"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: IdeaCreate) -> Idea | None:
        now = datetime.now(UTC)
        idea_id = str(uuid.uuid4())
        doc = {
            "id": idea_id,
            "userId": self._user_id or "default-user",
            "title": data.title,
            "description": data.description,
            "images": data.images,
            "attachments": data.attachments,
            "status": "draft",
            "refinedDraft": None,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[idea_id] = doc
        self._save_to_disk()
        logger.info("Created idea %s (in-memory)", idea_id)
        return self._doc_to_model(doc)

    async def list(self) -> list[Idea]:
        docs = sorted(self._user_items(), key=lambda d: d["updatedAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, idea_id: str) -> Idea | None:
        doc = self._store.get(idea_id)
        return self._doc_to_model(doc) if doc else None

    async def update(self, idea_id: str, data: IdeaUpdate) -> Idea | None:
        doc = self._store.get(idea_id)
        if not doc:
            return None
        if data.title is not None:
            doc["title"] = data.title
        if data.description is not None:
            doc["description"] = data.description
        if data.images is not None:
            doc["images"] = data.images
        if data.attachments is not None:
            doc["attachments"] = data.attachments
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        logger.info("Updated idea %s (in-memory)", idea_id)
        return self._doc_to_model(doc)

    async def delete(self, idea_id: str) -> bool:
        if idea_id in self._store:
            del self._store[idea_id]
            self._save_to_disk()
            logger.info("Deleted idea %s (in-memory)", idea_id)
            return True
        return False

    async def set_refined(self, idea_id: str, draft: str) -> Idea | None:
        """Store the refined draft and mark status as refined."""
        doc = self._store.get(idea_id)
        if not doc:
            return None
        doc["refinedDraft"] = draft
        doc["status"] = "refined"
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)
