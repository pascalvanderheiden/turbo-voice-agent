"""In-memory research service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.research import Citation, Research, ResearchCreate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)


class InMemoryResearchService(JsonPersistenceMixin):
    """In-memory CRUD for research entries with JSON file persistence."""


    _json_file = "research.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def _doc_to_model(self, doc: dict) -> Research:
        return Research(
            id=doc["id"],
            title=doc["title"],
            query=doc["query"],
            mode=doc["mode"],
            status=doc.get("status", "pending"),
            result=doc.get("result"),
            citations=[Citation(**c) for c in doc.get("citations", [])],
            ideaId=doc.get("ideaId"),
            error=doc.get("error"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: ResearchCreate) -> Research:
        now = datetime.now(UTC)
        rid = str(uuid.uuid4())
        doc = {
            "id": rid,
            "userId": self._user_id or "default-user",
            "title": data.query[:80],
            "query": data.query,
            "mode": data.mode,
            "status": "pending",
            "result": None,
            "citations": [],
            "ideaId": data.idea_id,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[rid] = doc
        self._save_to_disk()
        logger.info("Created research %s (in-memory)", rid)
        return self._doc_to_model(doc)

    async def list(self) -> list[Research]:
        docs = sorted(self._user_items(), key=lambda d: d["createdAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, rid: str) -> Research | None:
        doc = self._store.get(rid)
        return self._doc_to_model(doc) if doc else None

    async def delete(self, rid: str) -> bool:
        if rid in self._store:
            del self._store[rid]
            self._save_to_disk()
            return True
        return False

    async def list_by_idea(self, idea_id: str) -> list[Research]:
        docs = [d for d in self._store.values() if d.get("ideaId") == idea_id]
        docs.sort(key=lambda d: d["createdAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def set_result(self, rid: str, result: str, citations: list[dict]) -> Research | None:
        doc = self._store.get(rid)
        if not doc:
            return None
        doc["result"] = result
        doc["citations"] = citations
        doc["status"] = "completed"
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def set_failed(self, rid: str, error: str) -> Research | None:
        doc = self._store.get(rid)
        if not doc:
            return None
        doc["error"] = error
        doc["status"] = "failed"
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def link_to_idea(self, rid: str, idea_id: str | None) -> Research | None:
        """Link (or unlink) a research entry to an idea."""
        doc = self._store.get(rid)
        if not doc:
            return None
        doc["ideaId"] = idea_id
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)
