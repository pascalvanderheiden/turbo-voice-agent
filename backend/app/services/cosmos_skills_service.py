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
        """Delete the skill document from Cosmos DB."""
        try:
            container = await self._container()
            await container.delete_item(item=name, partition_key=self._user_id)
            logger.info("Deactivated skill '%s' for user %s", name, self._user_id)
        except CosmosResourceNotFoundError:
            logger.debug("Skill '%s' not found — nothing to deactivate", name)
        except Exception:
            logger.exception("Failed to deactivate skill '%s'", name)
            raise

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
        """Return a mapping of skill name → npxCommand for all requested skills."""
        if not skill_ids:
            return {}
        result: dict[str, str] = {}
        for name in skill_ids:
            skill = await self.get_skill(name)
            if skill and skill.get("npxCommand"):
                result[name] = skill["npxCommand"]
        return result
