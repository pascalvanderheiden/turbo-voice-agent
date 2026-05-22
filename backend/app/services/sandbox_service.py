"""Cosmos DB-backed service for per-user sandbox state."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, SANDBOX_STATE_CONTAINER_ID
from app.models.sandbox import SandboxConfig, SandboxState

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class SandboxService:
    """Service layer for sandbox state backed by Cosmos DB."""

    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> SandboxService:
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(SANDBOX_STATE_CONTAINER_ID)

    def _doc_to_model(self, doc: dict) -> SandboxState:
        """Convert a Cosmos DB document to a SandboxState model.

        Tolerates legacy documents containing the obsolete ``containerAppUrl``
        field (Phase 3 of ``sandbox-dynamic-sessions``): we silently ignore it
        on read and never write it back. No batch migration needed since
        sandbox state resets per dev-task.
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

    def _model_to_doc(self, state: SandboxState) -> dict:
        """Convert a SandboxState model to a Cosmos DB document.

        Never writes the deprecated ``containerAppUrl`` field. Older documents
        that still contain it are not actively cleaned up; they're simply
        ignored on read.
        """
        return {
            "id": state.id,
            "userId": self._user_id,
            "status": state.status,
            "skillsHash": state.skills_hash,
            "githubConnected": state.github_connected,
            "config": state.config.model_dump(),
            "sessionIdentifier": state.session_identifier,
            "docType": "sandbox_state",
            "createdAt": state.created_at.isoformat()
            if isinstance(state.created_at, datetime)
            else state.created_at,
            "updatedAt": state.updated_at.isoformat()
            if isinstance(state.updated_at, datetime)
            else state.updated_at,
        }

    async def get_state(self) -> SandboxState | None:
        """Get sandbox state for the current user."""
        try:
            container = await self._container()
            query = "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'sandbox_state'"
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id
            )
            async for doc in items:
                return self._doc_to_model(doc)
            return None
        except Exception:
            logger.exception("Failed to get sandbox state for user %s", self._user_id)
            return None

    async def upsert_state(self, state: SandboxState) -> SandboxState | None:
        """Upsert sandbox state for the current user."""
        try:
            container = await self._container()
            doc = self._model_to_doc(state)
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to upsert sandbox state")
            return None

    async def update_config(self, config: SandboxConfig) -> SandboxState | None:
        """Update sandbox config (model selection etc)."""
        try:
            container = await self._container()
            existing = await self.get_state()
            if not existing:
                now = datetime.now(UTC)
                state = SandboxState(
                    id=str(uuid.uuid4()),
                    userId=self._user_id,
                    config=config,
                    createdAt=now,
                    updatedAt=now,
                )
                doc = self._model_to_doc(state)
                result = await container.upsert_item(doc)
                return self._doc_to_model(result)
            doc = self._model_to_doc(existing)
            doc["config"] = config.model_dump()
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to update sandbox config")
            return None

    async def set_status(self, status: str) -> SandboxState | None:
        """Update the status field of sandbox state."""
        try:
            container = await self._container()
            existing = await self.get_state()
            if not existing:
                now = datetime.now(UTC)
                state = SandboxState(
                    id=str(uuid.uuid4()),
                    userId=self._user_id,
                    status=status,
                    createdAt=now,
                    updatedAt=now,
                )
                doc = self._model_to_doc(state)
                result = await container.upsert_item(doc)
                return self._doc_to_model(result)
            doc = self._model_to_doc(existing)
            doc["status"] = status
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to set sandbox status")
            return None

    async def set_github_connected(self, connected: bool) -> SandboxState | None:
        """Set the GitHub auth connection status."""
        try:
            container = await self._container()
            existing = await self.get_state()
            if not existing:
                now = datetime.now(UTC)
                state = SandboxState(
                    id=str(uuid.uuid4()),
                    userId=self._user_id,
                    githubConnected=connected,
                    createdAt=now,
                    updatedAt=now,
                )
                doc = self._model_to_doc(state)
                result = await container.upsert_item(doc)
                return self._doc_to_model(result)
            doc = self._model_to_doc(existing)
            doc["githubConnected"] = connected
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to set github connected status")
            return None

    async def delete_state(self) -> bool:
        """Delete sandbox state for the current user."""
        try:
            existing = await self.get_state()
            if not existing:
                return False
            container = await self._container()
            await container.delete_item(item=existing.id, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete sandbox state")
            return False
