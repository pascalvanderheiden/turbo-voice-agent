"""SpecService — CRUD operations for specs against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, SPECS_CONTAINER_ID
from app.models.spec import Spec, SpecCreate, SpecUpdate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class SpecService:
    """Service layer for specs CRUD backed by Cosmos DB."""


    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> "SpecService":
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(SPECS_CONTAINER_ID)

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
        try:
            container = await self._container()
            now = datetime.now(UTC)
            spec_id = str(uuid.uuid4())
            doc = {
                "id": spec_id,
                "userId": self._user_id,
                "title": data.title,
                "content": data.content,
                "type": data.type,
                "parentId": data.parent_id,
                "ideaId": data.idea_id,
                "status": "draft",
                "docType": "spec",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to create spec")
            return None

    async def list(self) -> list[Spec]:
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'spec' "
                "ORDER BY c.updatedAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            docs = [doc async for doc in items]
            # Sort: foundation first, then features
            foundations = [d for d in docs if d.get("type") == "foundation"]
            features = [d for d in docs if d.get("type") != "foundation"]
            return [self._doc_to_model(d) for d in foundations + features]
        except Exception:
            logger.exception("Failed to list specs")
            return []

    async def get_by_id(self, spec_id: str) -> Spec | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=spec_id, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get spec %s", spec_id)
            return None

    async def update(self, spec_id: str, data: SpecUpdate) -> Spec | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=spec_id, partition_key=self._user_id)
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
            result = await container.replace_item(item=spec_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to update spec %s", spec_id)
            return None

    async def delete(self, spec_id: str) -> bool:
        try:
            container = await self._container()
            await container.delete_item(item=spec_id, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete spec %s", spec_id)
            return False

    async def set_optimized(self, spec_id: str, content: str) -> Spec | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=spec_id, partition_key=self._user_id)
            doc["content"] = content
            doc["status"] = "optimized"
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.replace_item(item=spec_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to optimize spec %s", spec_id)
            return None

    async def list_by_idea(self, idea_id: str) -> list[Spec]:
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'spec' "
                "AND c.ideaId = @ideaId ORDER BY c.updatedAt DESC"
            )
            params = [
                {"name": "@userId", "value": self._user_id},
                {"name": "@ideaId", "value": idea_id},
            ]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            docs = [doc async for doc in items]
            foundations = [d for d in docs if d.get("type") == "foundation"]
            features = [d for d in docs if d.get("type") != "foundation"]
            return [self._doc_to_model(d) for d in foundations + features]
        except Exception:
            logger.exception("Failed to list specs for idea %s", idea_id)
            return []

    async def get_features_for_foundation(self, foundation_id: str) -> list[Spec]:
        """Get all feature specs that have this foundation as parent."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'spec' "
                "AND c.parentId = @parentId AND c.type = 'feature' "
                "ORDER BY c.createdAt ASC"
            )
            params = [
                {"name": "@userId", "value": self._user_id},
                {"name": "@parentId", "value": foundation_id},
            ]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to get features for foundation %s", foundation_id)
            return []

    async def set_dev_task_id(self, spec_id: str, dev_task_id: str | None, status: str | None = None) -> Spec | None:
        """Link a spec to a dev task and optionally update status."""
        try:
            container = await self._container()
            doc = await container.read_item(item=spec_id, partition_key=self._user_id)
            doc["devTaskId"] = dev_task_id
            if status:
                doc["status"] = status
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.replace_item(item=spec_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set dev task ID on spec %s", spec_id)
            return None
