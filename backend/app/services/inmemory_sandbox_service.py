"""In-memory fallback for sandbox state with JSON file persistence."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.sandbox import SandboxConfig, SandboxState
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class InMemorySandboxService(JsonPersistenceMixin):
    """In-memory sandbox state service with JSON file persistence."""

    _json_file = "sandbox_state.json"

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._load_from_disk()

    def _doc_to_model(self, doc: dict) -> SandboxState:
        """Convert a stored dict to a SandboxState model.

        Tolerates legacy ``containerAppUrl`` field (ignored). See
        ``SandboxService._doc_to_model`` for the lazy-upgrade rationale.
        """
        return SandboxState(
            id=doc["id"],
            userId=doc["userId"],
            status=doc.get("status", "stopped"),
            skillsHash=doc.get("skillsHash"),
            githubConnected=doc.get("githubConnected", False),
            config=SandboxConfig(**doc["config"]) if doc.get("config") else SandboxConfig(),
            sessionIdentifier=doc.get("sessionIdentifier"),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    def _find_user_doc(self) -> dict | None:
        """Find the sandbox state document for the current user."""
        for doc in self._user_items():
            if doc.get("docType") == "sandbox_state":
                return doc
        return None

    async def get_state(self) -> SandboxState | None:
        """Get sandbox state for the current user."""
        doc = self._find_user_doc()
        return self._doc_to_model(doc) if doc else None

    async def upsert_state(self, state: SandboxState) -> SandboxState:
        """Upsert sandbox state for the current user."""
        doc = {
            "id": state.id,
            "userId": self._user_id or DEFAULT_USER_ID,
            "status": state.status,
            "skillsHash": state.skills_hash,
            "githubConnected": state.github_connected,
            "config": state.config.model_dump(),
            "sessionIdentifier": state.session_identifier,
            "docType": "sandbox_state",
            "createdAt": state.created_at.isoformat()
            if isinstance(state.created_at, datetime)
            else state.created_at,
            "updatedAt": datetime.now(UTC).isoformat(),
        }
        self._store[doc["id"]] = doc
        self._save_to_disk()
        logger.info("Upserted sandbox state %s (in-memory)", doc["id"])
        return self._doc_to_model(doc)

    async def update_config(self, config: SandboxConfig) -> SandboxState:
        """Update sandbox config (model selection etc)."""
        existing = self._find_user_doc()
        now = datetime.now(UTC)
        if not existing:
            state_id = str(uuid.uuid4())
            doc = {
                "id": state_id,
                "userId": self._user_id or DEFAULT_USER_ID,
                "status": "stopped",
                "skillsHash": None,
                "githubConnected": False,
                "config": config.model_dump(),
                "sessionIdentifier": None,
                "docType": "sandbox_state",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            self._store[state_id] = doc
            self._save_to_disk()
            logger.info("Created sandbox state %s (in-memory)", state_id)
            return self._doc_to_model(doc)
        existing["config"] = config.model_dump()
        existing["updatedAt"] = now.isoformat()
        self._save_to_disk()
        logger.info("Updated sandbox config %s (in-memory)", existing["id"])
        return self._doc_to_model(existing)

    async def set_status(self, status: str) -> SandboxState:
        """Update the status field of sandbox state."""
        existing = self._find_user_doc()
        now = datetime.now(UTC)
        if not existing:
            state_id = str(uuid.uuid4())
            doc = {
                "id": state_id,
                "userId": self._user_id or DEFAULT_USER_ID,
                "status": status,
                "skillsHash": None,
                "githubConnected": False,
                "config": SandboxConfig().model_dump(),
                "sessionIdentifier": None,
                "docType": "sandbox_state",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            self._store[state_id] = doc
            self._save_to_disk()
            logger.info("Created sandbox state %s (in-memory)", state_id)
            return self._doc_to_model(doc)
        existing["status"] = status
        existing["updatedAt"] = now.isoformat()
        self._save_to_disk()
        logger.info("Updated sandbox status %s (in-memory)", existing["id"])
        return self._doc_to_model(existing)

    async def set_github_connected(self, connected: bool) -> SandboxState:
        """Set the GitHub auth connection status."""
        existing = self._find_user_doc()
        now = datetime.now(UTC)
        if not existing:
            state_id = str(uuid.uuid4())
            doc = {
                "id": state_id,
                "userId": self._user_id or DEFAULT_USER_ID,
                "status": "stopped",
                "skillsHash": None,
                "githubConnected": connected,
                "config": SandboxConfig().model_dump(),
                "sessionIdentifier": None,
                "docType": "sandbox_state",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            self._store[state_id] = doc
            self._save_to_disk()
            logger.info("Created sandbox state %s (in-memory)", state_id)
            return self._doc_to_model(doc)
        existing["githubConnected"] = connected
        existing["updatedAt"] = now.isoformat()
        self._save_to_disk()
        logger.info("Updated github connected %s (in-memory)", existing["id"])
        return self._doc_to_model(existing)

    async def delete_state(self) -> bool:
        """Delete sandbox state for the current user."""
        doc = self._find_user_doc()
        if not doc:
            return False
        del self._store[doc["id"]]
        self._save_to_disk()
        logger.info("Deleted sandbox state %s (in-memory)", doc["id"])
        return True
