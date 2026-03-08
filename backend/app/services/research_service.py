"""ResearchService — CRUD operations for research against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, RESEARCH_CONTAINER_ID
from app.models.research import Citation, Research, ResearchCreate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class ResearchService:
    """Service layer for research CRUD backed by Cosmos DB."""


    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> "ResearchService":
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(RESEARCH_CONTAINER_ID)

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
        container = await self._container()
        now = datetime.now(UTC)
        rid = str(uuid.uuid4())
        doc = {
            "id": rid,
            "userId": self._user_id,
            "title": data.query[:80],
            "query": data.query,
            "mode": data.mode,
            "status": "pending",
            "result": None,
            "citations": [],
            "ideaId": data.idea_id,
            "error": None,
            "docType": "research",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        result = await container.upsert_item(doc)
        logger.info("Created research %s (Cosmos DB)", rid)
        return self._doc_to_model(result)

    async def list(self) -> list[Research]:
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'research' "
                "ORDER BY c.createdAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list research")
            return []

    async def get_by_id(self, rid: str) -> Research | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=rid, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get research %s", rid)
            return None

    async def delete(self, rid: str) -> bool:
        try:
            container = await self._container()
            await container.delete_item(item=rid, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete research %s", rid)
            return False

    async def list_by_idea(self, idea_id: str) -> list[Research]:
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'research' "
                "AND c.ideaId = @ideaId ORDER BY c.createdAt DESC"
            )
            params = [
                {"name": "@userId", "value": self._user_id},
                {"name": "@ideaId", "value": idea_id},
            ]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list research for idea %s", idea_id)
            return []

    async def set_result(self, rid: str, result: str, citations: list[dict]) -> Research | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=rid, partition_key=self._user_id)
            doc["result"] = result
            doc["citations"] = citations
            doc["status"] = "completed"
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            updated = await container.replace_item(item=rid, body=doc)
            return self._doc_to_model(updated)
        except Exception:
            logger.exception("Failed to set result for research %s", rid)
            return None

    async def set_failed(self, rid: str, error: str) -> Research | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=rid, partition_key=self._user_id)
            doc["error"] = error
            doc["status"] = "failed"
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            updated = await container.replace_item(item=rid, body=doc)
            return self._doc_to_model(updated)
        except Exception:
            logger.exception("Failed to set failed for research %s", rid)
            return None
