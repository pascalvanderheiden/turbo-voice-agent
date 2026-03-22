"""In-memory slides service — same pattern as InMemoryBrainstormService."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.slides import Slides, SlidesCreate, SlidesUpdate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)


class InMemorySlidesService(JsonPersistenceMixin):
    """In-memory CRUD for presentations with JSON file persistence."""

    _json_file = "slides.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def _doc_to_model(self, doc: dict) -> Slides:
        return Slides(
            id=doc["id"],
            title=doc["title"],
            description=doc.get("description", ""),
            sections=doc.get("sections", []),
            attachments=doc.get("attachments", []),
            subtitle=doc.get("subtitle", ""),
            icon=doc.get("icon", ""),
            theme=doc.get("theme", "shadcn/ui"),
            appearance=doc.get("appearance", "dark"),
            palette=doc.get("palette", "arctic"),
            status=doc.get("status", "draft"),
            refinedDraft=doc.get("refinedDraft"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: SlidesCreate) -> Slides | None:
        now = datetime.now(UTC)
        slides_id = str(uuid.uuid4())
        doc = {
            "id": slides_id,
            "userId": self._user_id or "default-user",
            "title": data.title,
            "description": data.description,
            "sections": [s.model_dump(by_alias=True) for s in data.sections],
            "attachments": data.attachments,
            "subtitle": data.subtitle,
            "icon": data.icon,
            "theme": data.theme,
            "appearance": data.appearance,
            "palette": data.palette,
            "status": "draft",
            "refinedDraft": None,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[slides_id] = doc
        self._save_to_disk()
        logger.info("Created slides %s (in-memory)", slides_id)
        return self._doc_to_model(doc)

    async def list(self) -> list[Slides]:
        docs = sorted(self._user_items(), key=lambda d: d["updatedAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, slides_id: str) -> Slides | None:
        doc = self._store.get(slides_id)
        return self._doc_to_model(doc) if doc else None

    async def update(self, slides_id: str, data: SlidesUpdate) -> Slides | None:
        doc = self._store.get(slides_id)
        if not doc:
            return None
        if data.title is not None:
            doc["title"] = data.title
        if data.description is not None:
            doc["description"] = data.description
        if data.sections is not None:
            doc["sections"] = [s.model_dump(by_alias=True) for s in data.sections]
        if data.attachments is not None:
            doc["attachments"] = data.attachments
        if data.subtitle is not None:
            doc["subtitle"] = data.subtitle
        if data.icon is not None:
            doc["icon"] = data.icon
        if data.theme is not None:
            doc["theme"] = data.theme
        if data.appearance is not None:
            doc["appearance"] = data.appearance
        if data.palette is not None:
            doc["palette"] = data.palette
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        logger.info("Updated slides %s (in-memory)", slides_id)
        return self._doc_to_model(doc)

    async def delete(self, slides_id: str) -> bool:
        if slides_id in self._store:
            del self._store[slides_id]
            self._save_to_disk()
            logger.info("Deleted slides %s (in-memory)", slides_id)
            return True
        return False

    async def set_refined(self, slides_id: str, draft: str) -> Slides | None:
        """Store the refined draft and mark status as refined."""
        doc = self._store.get(slides_id)
        if not doc:
            return None
        doc["refinedDraft"] = draft
        doc["status"] = "refined"
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)
