"""BrainstormService — CRUD operations for ideas against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, IDEAS_CONTAINER_ID
from app.models.idea import Idea, IdeaCreate, IdeaUpdate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class BrainstormService:
    """Service layer for ideas CRUD backed by Cosmos DB."""


    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> BrainstormService:
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(IDEAS_CONTAINER_ID)

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
        try:
            container = await self._container()
            now = datetime.now(UTC)
            idea_id = str(uuid.uuid4())
            doc = {
                "id": idea_id,
                "userId": self._user_id,
                "title": data.title,
                "description": data.description,
                "images": data.images,
                "attachments": data.attachments,
                "status": "draft",
                "refinedDraft": None,
                "docType": "idea",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to create idea")
            return None

    async def list(self) -> list[Idea]:
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'idea' "
                "ORDER BY c.updatedAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query, parameters=params, partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list ideas")
            return []

    async def get_by_id(self, idea_id: str) -> Idea | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=idea_id, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get idea %s", idea_id)
            return None

    async def update(self, idea_id: str, data: IdeaUpdate) -> Idea | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=idea_id, partition_key=self._user_id)
            if data.title is not None:
                doc["title"] = data.title
            if data.description is not None:
                doc["description"] = data.description
            if data.images is not None:
                doc["images"] = data.images
            if data.attachments is not None:
                doc["attachments"] = data.attachments
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.replace_item(item=idea_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to update idea %s", idea_id)
            return None

    async def delete(self, idea_id: str) -> bool:
        try:
            container = await self._container()
            await container.delete_item(item=idea_id, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete idea %s", idea_id)
            return False

    async def set_refined(self, idea_id: str, draft: str) -> Idea | None:
        try:
            container = await self._container()
            doc = await container.read_item(item=idea_id, partition_key=self._user_id)
            doc["refinedDraft"] = draft
            doc["status"] = "refined"
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.replace_item(item=idea_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to refine idea %s", idea_id)
            return None
