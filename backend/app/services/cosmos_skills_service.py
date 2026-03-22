"""CosmosSkillsService — activation-based skill management backed by Cosmos DB.

Skills are now simply *activated* (metadata + npx command stored in Cosmos)
rather than downloaded to the filesystem.  At pipeline time the stored
``npxCommand`` is executed inside the sandbox.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, SKILLS_CONTAINER_ID

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class CosmosSkillsService:
    """Manages activated skills per user in Cosmos DB."""

    def __init__(self, cosmos_client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._cosmos = cosmos_client
        self._user_id = user_id

    def with_user(self, user_id: str) -> CosmosSkillsService:
        """Return a view of this service scoped to a specific user."""
        return CosmosSkillsService(self._cosmos, user_id)

    async def _container(self):
        db = self._cosmos.get_database_client(DATABASE_ID)
        return db.get_container_client(SKILLS_CONTAINER_ID)

    # ── Activate / deactivate ─────────────────────────────────────────

    async def activate_skill(
        self,
        name: str,
        description: str,
        source: str,
        npx_command: str,
    ) -> dict:
        """Upsert an activated skill document for the current user."""
        now = datetime.now(UTC).isoformat()
        doc = {
            "id": name,
            "userId": self._user_id,
            "docType": "skill",
            "name": name,
            "description": description,
            "source": source,
            "npxCommand": npx_command,
            "activatedAt": now,
            "updatedAt": now,
        }
        try:
            container = await self._container()
            await container.upsert_item(doc)
            logger.info("Activated skill '%s' for user %s", name, self._user_id)
            return doc
        except Exception:
            logger.exception("Failed to activate skill '%s'", name)
            raise

    async def deactivate_skill(self, name: str) -> None:
        """Delete the skill document from Cosmos DB and blob storage."""
        try:
            container = await self._container()
            await container.delete_item(item=name, partition_key=self._user_id)

            # Clean up blob storage for any skills that may have blob files
            await self._delete_skill_blobs(name)

            logger.info("Deactivated skill '%s' for user %s", name, self._user_id)
        except CosmosResourceNotFoundError:
            logger.debug("Skill '%s' not found — nothing to deactivate", name)
        except Exception:
            logger.exception("Failed to deactivate skill '%s'", name)
            raise

    async def _delete_skill_blobs(self, skill_name: str) -> None:
        """Delete all blobs for a local skill from Azure Blob Storage."""
        import os

        storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        if not storage_account:
            logger.warning("AZURE_STORAGE_ACCOUNT_NAME not set — skipping blob cleanup for '%s'", skill_name)
            return

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.storage.blob.aio import BlobServiceClient

            credential = DefaultAzureCredential()
            blob_service = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential,
            )
            deleted = 0
            async with blob_service:
                container = blob_service.get_container_client("skills")
                async for blob in container.list_blobs(name_starts_with=f"{skill_name}/"):
                    await container.delete_blob(blob.name)
                    deleted += 1
                    logger.info("Deleted skill blob: %s", blob.name)
            await credential.close()
            logger.info("Cleaned up %d blob(s) for local skill '%s'", deleted, skill_name)
        except Exception:
            logger.exception("Failed to delete blobs for skill '%s' — Cosmos record already removed", skill_name)

    # ── Read ──────────────────────────────────────────────────────────

    # ── Marketplace skill blob upload ─────────────────────────────────

    async def upload_skill_from_github_to_blob(
        self, skill_name: str, repo: str,
    ) -> list[str]:
        """Download skill files from GitHub and upload to blob storage.

        Args:
            skill_name: Skill directory name within the repo.
            repo: GitHub repo in ``owner/repo`` format.

        Returns:
            List of uploaded blob paths, empty on failure.
        """
        import os

        import httpx

        storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        if not storage_account:
            logger.warning(
                "AZURE_STORAGE_ACCOUNT_NAME not set — skipping blob upload for '%s'",
                skill_name,
            )
            return []

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.storage.blob.aio import BlobServiceClient

            # Fetch files from GitHub
            github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
            if github_token:
                headers["Authorization"] = f"token {github_token}"

            files_to_upload: list[tuple[str, bytes]] = []
            async with httpx.AsyncClient(timeout=30) as client:
                await self._fetch_github_dir(
                    client, repo, skill_name, skill_name, headers, files_to_upload,
                )

            if not files_to_upload:
                logger.warning(
                    "No files found on GitHub for skill '%s' at %s/%s",
                    skill_name, repo, skill_name,
                )
                return []

            # Upload to blob storage
            credential = DefaultAzureCredential()
            blob_service = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential,
            )
            uploaded: list[str] = []
            async with blob_service:
                container = blob_service.get_container_client("skills")
                try:
                    await container.create_container()
                except Exception:
                    pass
                for rel_path, content in files_to_upload:
                    blob_path = f"{skill_name}/{rel_path}"
                    blob_client = container.get_blob_client(blob_path)
                    await blob_client.upload_blob(content, overwrite=True)
                    uploaded.append(blob_path)
                    logger.info("Uploaded marketplace skill file: %s", blob_path)
            await credential.close()

            logger.info(
                "Uploaded %d file(s) for marketplace skill '%s'", len(uploaded), skill_name,
            )
            return uploaded
        except Exception:
            logger.exception("Failed to upload marketplace skill '%s' to blob", skill_name)
            return []

    async def _fetch_github_dir(
        self,
        client,
        repo: str,
        dir_path: str,
        base_dir: str,
        headers: dict[str, str],
        result: list[tuple[str, bytes]],
    ) -> None:
        """Recursively fetch files from a GitHub repo directory."""
        url = f"https://api.github.com/repos/{repo}/contents/{dir_path}"
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        items = resp.json()

        if isinstance(items, dict):
            items = [items]

        for item in items:
            if item["type"] == "file" and item.get("download_url"):
                file_resp = await client.get(item["download_url"])
                file_resp.raise_for_status()
                rel_path = item["path"].removeprefix(base_dir).lstrip("/")
                result.append((rel_path, file_resp.content))
            elif item["type"] == "dir":
                await self._fetch_github_dir(
                    client, repo, item["path"], base_dir, headers, result,
                )

    # ── Read ──────────────────────────────────────────────────────────

    async def list_activated(self) -> list[dict]:
        """Return all activated skills for the current user."""
        container = await self._container()
        query = (
            "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'skill' "
            "ORDER BY c.name"
        )
        params: list[dict] = [{"name": "@userId", "value": self._user_id}]
        items = container.query_items(
            query=query, parameters=params, partition_key=self._user_id
        )
        return [
            {
                "name": doc["name"],
                "description": doc.get("description", ""),
                "source": doc.get("source", ""),
                "npxCommand": doc.get("npxCommand", ""),
                "activatedAt": doc.get("activatedAt", ""),
            }
            async for doc in items
        ]

    async def get_skill(self, name: str) -> dict | None:
        """Read a single skill document, or *None* if it doesn't exist."""
        try:
            container = await self._container()
            doc = await container.read_item(item=name, partition_key=self._user_id)
            return {
                "name": doc["name"],
                "description": doc.get("description", ""),
                "source": doc.get("source", ""),
                "npxCommand": doc.get("npxCommand", ""),
                "activatedAt": doc.get("activatedAt", ""),
            }
        except CosmosResourceNotFoundError:
            return None

    async def get_npx_commands(self, skill_ids: list[str]) -> dict[str, str]:
        """Return a mapping of skill name → npxCommand for all requested skills.

        Local skills (source='local') always return '__local__' regardless of
        what npxCommand is stored, to handle legacy records with wrong degit URLs.
        """
        if not skill_ids:
            return {}
        result: dict[str, str] = {}
        for name in skill_ids:
            skill = await self.get_skill(name)
            if skill and skill.get("npxCommand"):
                if skill.get("source") == "local":
                    result[name] = "__local__"
                else:
                    result[name] = skill["npxCommand"]
        return result
