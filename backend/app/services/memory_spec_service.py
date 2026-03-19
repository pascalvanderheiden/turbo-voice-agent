"""In-memory spec service — same pattern as other in-memory services."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.spec import Spec, SpecCreate, SpecUpdate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)


class InMemorySpecService(JsonPersistenceMixin):
    """In-memory CRUD for specs with JSON file persistence."""


    _json_file = "specs.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def _doc_to_model(self, doc: dict) -> Spec:
        return Spec(
            id=doc["id"],
            title=doc["title"],
            content=doc.get("content", ""),
            type=doc.get("type", "foundation"),
            parentId=doc.get("parentId"),
            ideaId=doc.get("ideaId"),
            status=doc.get("status", "draft"),
            devTaskId=doc.get("devTaskId"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: SpecCreate) -> Spec | None:
        now = datetime.now(UTC)
        spec_id = str(uuid.uuid4())
        doc = {
            "id": spec_id,
            "userId": self._user_id or "default-user",
            "title": data.title,
            "content": data.content,
            "type": data.type,
            "parentId": data.parent_id,
            "ideaId": data.idea_id,
            "status": "draft",
            "formatVersion": data.format_version or "v2",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[spec_id] = doc
        self._save_to_disk()
        logger.info("Created spec %s (in-memory)", spec_id)
        return self._doc_to_model(doc)

    async def list(self) -> list[Spec]:
        docs = sorted(
            self._user_items(),
            key=lambda d: (0 if d.get("type") == "foundation" else 1, d["updatedAt"]),
        )
        # foundation first, then features by updatedAt
        foundations = [d for d in docs if d.get("type") == "foundation"]
        features = sorted(
            [d for d in docs if d.get("type") != "foundation"],
            key=lambda d: d["updatedAt"],
            reverse=True,
        )
        return [self._doc_to_model(d) for d in foundations + features]

    async def get_by_id(self, spec_id: str) -> Spec | None:
        doc = self._store.get(spec_id)
        return self._doc_to_model(doc) if doc else None

    async def update(self, spec_id: str, data: SpecUpdate) -> Spec | None:
        doc = self._store.get(spec_id)
        if not doc:
            return None
        if data.title is not None:
            doc["title"] = data.title
        if data.content is not None:
            doc["content"] = data.content
        if data.type is not None:
            doc["type"] = data.type
        if data.parent_id is not None:
            doc["parentId"] = data.parent_id
        if data.status is not None:
            doc["status"] = data.status
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        logger.info("Updated spec %s (in-memory)", spec_id)
        return self._doc_to_model(doc)

    async def delete(self, spec_id: str) -> bool:
        if spec_id in self._store:
            del self._store[spec_id]
            self._save_to_disk()
            logger.info("Deleted spec %s (in-memory)", spec_id)
            return True
        return False

    async def set_optimized(self, spec_id: str, content: str) -> Spec | None:
        """Store optimized content and mark status as optimized."""
        doc = self._store.get(spec_id)
        if not doc:
            return None
        doc["content"] = content
        doc["status"] = "optimized"
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def list_by_idea(self, idea_id: str) -> list[Spec]:
        """List specs linked to an idea."""
        docs = [d for d in self._store.values() if d.get("ideaId") == idea_id]
        foundations = sorted([d for d in docs if d.get("type") == "foundation"], key=lambda d: d["updatedAt"], reverse=True)
        features = sorted([d for d in docs if d.get("type") != "foundation"], key=lambda d: d["updatedAt"], reverse=True)
        return [self._doc_to_model(d) for d in foundations + features]

    async def get_features_for_foundation(self, foundation_id: str) -> list[Spec]:
        """Get all feature specs that have this foundation as parent."""
        docs = [d for d in self._store.values() if d.get("parentId") == foundation_id and d.get("type") == "feature"]
        docs.sort(key=lambda d: d["createdAt"])
        return [self._doc_to_model(d) for d in docs]

    async def set_dev_task_id(self, spec_id: str, dev_task_id: str | None, status: str | None = None) -> Spec | None:
        """Link a spec to a dev task and optionally update status."""
        doc = self._store.get(spec_id)
        if not doc:
            return None
        doc["devTaskId"] = dev_task_id
        if status:
            doc["status"] = status
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)
