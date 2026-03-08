"""MarketingService — CRUD operations for marketing videos against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, MARKETING_CONTAINER_ID
from app.models.marketing import MarketingVideo, MarketingVideoCreate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class MarketingService:
    """Service layer for marketing videos CRUD backed by Cosmos DB."""

    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> "MarketingService":
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(MARKETING_CONTAINER_ID)

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
        """Create a new marketing video record."""
        try:
            container = await self._container()
            now = datetime.now(UTC)
            vid = str(uuid.uuid4())
            doc = {
                "id": vid,
                "userId": self._user_id,
                "docType": "marketing_video",
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
            result = await container.upsert_item(doc)
            logger.info("Created marketing video %s", vid)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to create marketing video")
            return None

    async def list(self) -> list[MarketingVideo]:
        """List all marketing videos for the current user."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'marketing_video' "
                "ORDER BY c.createdAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query,
                parameters=params,
                partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list marketing videos")
            return []

    async def get_by_id(self, vid: str) -> MarketingVideo | None:
        """Get a single marketing video by ID."""
        try:
            container = await self._container()
            doc = await container.read_item(item=vid, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get marketing video %s", vid)
            return None

    async def delete(self, vid: str) -> bool:
        """Delete a marketing video by ID. Does NOT delete video files."""
        try:
            container = await self._container()
            await container.delete_item(item=vid, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete marketing video %s", vid)
            return False

    async def list_by_dev_task(self, dev_task_id: str) -> list[MarketingVideo]:
        """List marketing videos linked to a specific dev task."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'marketing_video' "
                "AND c.devTaskId = @devTaskId ORDER BY c.createdAt DESC"
            )
            params = [
                {"name": "@userId", "value": self._user_id},
                {"name": "@devTaskId", "value": dev_task_id},
            ]
            items = container.query_items(
                query=query,
                parameters=params,
                partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list marketing videos for dev task %s", dev_task_id)
            return []

    async def set_status(self, vid: str, status: str, **kwargs) -> MarketingVideo | None:
        """Update status and optional fields on a marketing video."""
        try:
            container = await self._container()
            doc = await container.read_item(item=vid, partition_key=self._user_id)
            doc["status"] = status
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            for k, v in kwargs.items():
                # Convert snake_case keys to camelCase
                camel = k
                if "_" in k:
                    parts = k.split("_")
                    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
                doc[camel] = v
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set status on marketing video %s", vid)
            return None
