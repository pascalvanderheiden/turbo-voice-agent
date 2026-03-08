"""CosmosSkillsService — SkillsService with Cosmos DB metadata + Azure Blob Storage files.

Extends the filesystem-based SkillsService so the dev-agent can still
read skill content from the local ```.agents/skills/``` directory, while
metadata lives in Cosmos and files are durably stored in Blob.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, SKILLS_CONTAINER_ID
from app.services.blob_skills_storage import BlobSkillsStorage
from app.services.skills_service import SKILLS_DIR, SkillsService, _parse_skill_md

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class CosmosSkillsService(SkillsService):
    """SkillsService backed by Cosmos DB (metadata) + Azure Blob Storage (files)."""

    def __init__(
        self,
        cosmos_client: CosmosClient,
        blob_storage: BlobSkillsStorage,
        user_id: str = DEFAULT_USER_ID,
        skills_dir: Path | None = None,
    ):
        super().__init__(skills_dir=skills_dir)
        self._cosmos = cosmos_client
        self._blob = blob_storage
        self._user_id = user_id

    def with_user(self, user_id: str) -> "CosmosSkillsService":
        """Return a view of this service scoped to a specific user."""
        return CosmosSkillsService(self._cosmos, self._blob, user_id, self._dir)

    async def _container(self):
        db = self._cosmos.get_database_client(DATABASE_ID)
        return db.get_container_client(SKILLS_CONTAINER_ID)

    # ── Startup sync ──────────────────────────────────────────────────

    async def sync_from_blob(self) -> None:
        """Download all skills from Blob Storage to local filesystem."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            await self._blob.sync_all(self._dir)
        except Exception:
            logger.exception("Failed to sync skills from Blob Storage")

    # ── Persist helpers ───────────────────────────────────────────────

    async def persist_skill(self, name: str) -> None:
        """Upload skill files to Blob and save metadata to Cosmos."""
        skill_dir = self._dir / name
        if not skill_dir.exists():
            logger.warning("Cannot persist skill '%s' — directory not found", name)
            return
        # Upload files to Blob
        try:
            await self._blob.upload_skill(name, skill_dir)
        except Exception:
            logger.exception("Failed to upload skill '%s' to Blob", name)
        # Save metadata to Cosmos
        try:
            meta = _parse_skill_md(skill_dir)
            container = await self._container()
            doc = {
                "id": name,
                "userId": self._user_id,
                "docType": "skill",
                "name": meta.get("name", name),
                "description": meta.get("description", ""),
                "version": meta.get("version", ""),
                "source": meta.get("source", "local"),
                "fileCount": meta.get("fileCount", 0),
                "installedAt": datetime.now(UTC).isoformat(),
                "updatedAt": datetime.now(UTC).isoformat(),
            }
            await container.upsert_item(doc)
            logger.info("Persisted skill '%s' metadata to Cosmos", name)
        except Exception:
            logger.exception("Failed to save skill '%s' metadata to Cosmos", name)

    async def remove_skill_data(self, name: str) -> None:
        """Delete skill files from Blob and metadata from Cosmos."""
        try:
            await self._blob.delete_skill(name)
        except Exception:
            logger.exception("Failed to delete skill '%s' from Blob", name)
        try:
            container = await self._container()
            await container.delete_item(item=name, partition_key=self._user_id)
            logger.info("Removed skill '%s' metadata from Cosmos", name)
        except CosmosResourceNotFoundError:
            pass
        except Exception:
            logger.exception("Failed to delete skill '%s' from Cosmos", name)

    # ── Overrides ─────────────────────────────────────────────────────

    async def install_from_marketplace(self, repo: str, skill_name: str) -> dict:
        """Install from marketplace, then persist to Blob + Cosmos."""
        result = await super().install_from_marketplace(repo, skill_name)
        if result.get("status") == "installed":
            await self.persist_skill(result.get("name", skill_name))
        return result

    def install_from_local(self, source_path: str, name: str) -> dict:
        """Install from local path. Caller must ``await persist_skill(name)``."""
        return super().install_from_local(source_path, name)

    def install_from_upload(self, name: str, files: dict[str, bytes]) -> dict:
        """Install from uploaded files. Caller must ``await persist_skill(name)``."""
        return super().install_from_upload(name, files)

    def uninstall(self, name: str) -> dict:
        """Remove locally. Caller must ``await remove_skill_data(name)``."""
        return super().uninstall(name)

    # ── List from Cosmos ──────────────────────────────────────────────

    async def list_from_cosmos(self) -> list[dict]:
        """List skill metadata from Cosmos DB."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'skill' "
                "ORDER BY c.name"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(query=query, parameters=params, partition_key=self._user_id)
            return [
                {
                    "name": doc["name"],
                    "description": doc.get("description", ""),
                    "version": doc.get("version", ""),
                    "source": doc.get("source", "local"),
                    "fileCount": doc.get("fileCount", 0),
                }
                async for doc in items
            ]
        except Exception:
            logger.exception("Failed to list skills from Cosmos — falling back to filesystem")
            return super().list_installed()
