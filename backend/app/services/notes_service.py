"""NotesService — CRUD operations for notes against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, NOTES_CONTAINER_ID
from app.models.note import Note, NoteCreate, NoteUpdate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class NotesService:
    """Service layer for notes CRUD backed by Cosmos DB."""


    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> "NotesService":
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(NOTES_CONTAINER_ID)

    def _doc_to_model(self, doc: dict) -> Note:
        return Note(
            id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            images=doc.get("images", []),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    def _model_to_doc(self, note_id: str, data: NoteCreate, now: datetime) -> dict:
        return {
            "id": note_id,
            "userId": self._user_id,
            "title": data.title,
            "content": data.content,
            "images": data.images,
            "docType": "note",
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }

    async def create(self, data: NoteCreate) -> Note | None:
        """Create a new note."""
        try:
            container = await self._container()
            now = datetime.now(UTC)
            note_id = str(uuid.uuid4())
            doc = self._model_to_doc(note_id, data, now)
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to create note")
            return None

    async def list(self) -> list[Note]:
        """List all notes for the current user, ordered by updatedAt desc."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'note' "
                "ORDER BY c.updatedAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query,
                parameters=params,
                partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list notes")
            return []

    async def get_by_id(self, note_id: str) -> Note | None:
        """Get a single note by ID."""
        try:
            container = await self._container()
            doc = await container.read_item(item=note_id, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get note %s", note_id)
            return None

    async def update(self, note_id: str, data: NoteUpdate) -> Note | None:
        """Update a note with partial fields."""
        try:
            container = await self._container()
            doc = await container.read_item(item=note_id, partition_key=self._user_id)
            if data.title is not None:
                doc["title"] = data.title
            if data.content is not None:
                doc["content"] = data.content
            if data.images is not None:
                doc["images"] = data.images
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.replace_item(item=note_id, body=doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to update note %s", note_id)
            return None

    async def delete(self, note_id: str) -> bool:
        """Delete a note by ID. Returns True if deleted, False otherwise."""
        try:
            container = await self._container()
            await container.delete_item(item=note_id, partition_key=self._user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete note %s", note_id)
            return False
