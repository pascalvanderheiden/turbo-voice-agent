"""Blob-backed file storage for agent skills."""

from __future__ import annotations

import logging
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger(__name__)

SKILLS_BLOB_CONTAINER = "skills"


class BlobSkillsStorage:
    """Upload / download skill file trees to Azure Blob Storage."""

    def __init__(self, account_name: str):
        self._account_url = f"https://{account_name}.blob.core.windows.net"
        self._credential = DefaultAzureCredential()
        self._container_name = SKILLS_BLOB_CONTAINER

    async def _client(self) -> BlobServiceClient:
        return BlobServiceClient(self._account_url, credential=self._credential)

    async def upload_skill(self, skill_name: str, local_dir: Path) -> int:
        """Upload all files from *local_dir* into ``skills/<skill_name>/``."""
        count = 0
        async with await self._client() as client:
            container = client.get_container_client(self._container_name)
            for file_path in local_dir.rglob("*"):
                if file_path.is_file():
                    blob_name = f"{skill_name}/{file_path.relative_to(local_dir)}"
                    data = file_path.read_bytes()
                    await container.upload_blob(blob_name, data, overwrite=True)
                    count += 1
        logger.info("Uploaded skill '%s' to Blob (%d files)", skill_name, count)
        return count

    async def download_skill(self, skill_name: str, local_dir: Path) -> int:
        """Download all blobs under ``skills/<skill_name>/`` to *local_dir*."""
        count = 0
        async with await self._client() as client:
            container = client.get_container_client(self._container_name)
            prefix = f"{skill_name}/"
            async for blob in container.list_blobs(name_starts_with=prefix):
                rel = blob.name[len(prefix):]
                dest = local_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                blob_client = container.get_blob_client(blob.name)
                stream = await blob_client.download_blob()
                dest.write_bytes(await stream.readall())
                count += 1
        logger.info("Downloaded skill '%s' from Blob (%d files)", skill_name, count)
        return count

    async def delete_skill(self, skill_name: str) -> int:
        """Delete all blobs for a skill."""
        count = 0
        async with await self._client() as client:
            container = client.get_container_client(self._container_name)
            prefix = f"{skill_name}/"
            async for blob in container.list_blobs(name_starts_with=prefix):
                await container.delete_blob(blob.name)
                count += 1
        logger.info("Deleted skill '%s' from Blob (%d files)", skill_name, count)
        return count

    async def list_skill_names(self) -> list[str]:
        """Return distinct top-level skill folder names in Blob."""
        names: set[str] = set()
        async with await self._client() as client:
            container = client.get_container_client(self._container_name)
            async for blob in container.list_blobs():
                parts = blob.name.split("/", 1)
                if parts:
                    names.add(parts[0])
        return sorted(names)

    async def sync_all(self, local_base: Path) -> int:
        """Download every skill from Blob into *local_base*/<skill>/."""
        skill_names = await self.list_skill_names()
        total = 0
        for name in skill_names:
            skill_dir = local_base / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            total += await self.download_skill(name, skill_dir)
        logger.info("Synced %d skills (%d files) from Blob Storage", len(skill_names), total)
        return total

    async def close(self) -> None:
        await self._credential.close()
