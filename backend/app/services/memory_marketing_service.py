"""In-memory marketing video service with JSON persistence."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.models.marketing import MarketingVideo, MarketingVideoCreate
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)


class InMemoryMarketingService(JsonPersistenceMixin):
    """In-memory CRUD for marketing videos with JSON file persistence."""


    _json_file = "marketing_videos.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def with_user(self, user_id: str):
        """No-op: in-memory service does not scope by user."""
        return self

    def _doc_to_model(self, doc: dict) -> MarketingVideo:
        return MarketingVideo(
            id=doc["id"],
            title=doc["title"],
            devTaskId=doc.get("devTaskId"),
            specId=doc.get("specId"),
            status=doc.get("status", "pending"),
            videoPath=doc.get("videoPath"),
            videoUrl=doc.get("videoUrl"),
            scriptContent=doc.get("scriptContent"),
            durationSeconds=doc.get("durationSeconds"),
            error=doc.get("error"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: MarketingVideoCreate) -> MarketingVideo:
        now = datetime.now(UTC)
        vid = str(uuid.uuid4())
        doc = {
            "id": vid,
            "title": data.title,
            "devTaskId": data.dev_task_id,
            "specId": None,
            "status": "pending",
            "videoPath": None,
            "scriptContent": None,
            "durationSeconds": None,
            "error": None,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[vid] = doc
        self._save_to_disk()
        logger.info("Created marketing video %s", vid)
        return self._doc_to_model(doc)

    async def list(self) -> list[MarketingVideo]:
        docs = sorted(self._store.values(), key=lambda d: d["createdAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, vid: str) -> MarketingVideo | None:
        doc = self._store.get(vid)
        return self._doc_to_model(doc) if doc else None

    async def delete(self, vid: str) -> bool:
        doc = self._store.get(vid)
        if not doc:
            return False
        # Delete video file if exists
        vpath = doc.get("videoPath")
        if vpath:
            try:
                Path(vpath).unlink(missing_ok=True)
            except Exception:
                logger.warning("Failed to delete video file %s", vpath)
        del self._store[vid]
        self._save_to_disk()
        return True

    async def list_by_dev_task(self, dev_task_id: str) -> list[MarketingVideo]:
        docs = [d for d in self._store.values() if d.get("devTaskId") == dev_task_id]
        docs.sort(key=lambda d: d["createdAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def set_status(self, vid: str, status: str, **kwargs) -> MarketingVideo | None:
        doc = self._store.get(vid)
        if not doc:
            return None
        doc["status"] = status
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        for k, v in kwargs.items():
            # Convert snake_case keys to camelCase
            camel = k
            if "_" in k:
                parts = k.split("_")
                camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            doc[camel] = v
        self._save_to_disk()
        return self._doc_to_model(doc)
