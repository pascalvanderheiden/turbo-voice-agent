"""In-memory skills service.

Drop-in replacement for CosmosSkillsService when Cosmos DB is unavailable.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class InMemorySkillsService:
    """In-memory skill activation management."""

    def __init__(self, user_id: str = DEFAULT_USER_ID):
        self._user_id = user_id
        self._store: dict[str, dict[str, dict]] = {}

    def with_user(self, user_id: str) -> InMemorySkillsService:
        """Return a view of this service scoped to a specific user."""
        return InMemorySkillsService._shared_view(self._store, user_id)

    @classmethod
    def _shared_view(cls, store: dict, user_id: str) -> InMemorySkillsService:
        """Create a new instance that shares the same store but with different user_id."""
        instance = cls(user_id)
        instance._store = store
        return instance

    async def activate_skill(
        self,
        name: str,
        description: str,
        source: str,
        npx_command: str,
    ) -> dict:
        """Upsert an activated skill for the current user."""
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
        if self._user_id not in self._store:
            self._store[self._user_id] = {}
        self._store[self._user_id][name] = doc
        logger.info("Activated skill '%s' for user %s (in-memory)", name, self._user_id)
        return doc

    async def deactivate_skill(self, name: str) -> None:
        """Remove the skill from in-memory storage."""
        if self._user_id in self._store and name in self._store[self._user_id]:
            del self._store[self._user_id][name]
            logger.info("Deactivated skill '%s' for user %s (in-memory)", name, self._user_id)
        else:
            logger.debug("Skill '%s' not found — nothing to deactivate", name)

    async def upload_skill_from_github_to_blob(self, skill_name: str, repo: str) -> list[str]:
        """No-op for in-memory service — blob storage unavailable without Cosmos."""
        logger.warning(
            "Blob upload skipped for skill '%s' — in-memory service has no blob storage",
            skill_name,
        )
        return []

    async def list_activated(self) -> list[dict]:
        """Return all activated skills for the current user."""
        if self._user_id not in self._store:
            return []
        skills = list(self._store[self._user_id].values())
        skills.sort(key=lambda s: s.get("name", ""))
        return [
            {
                "name": doc["name"],
                "description": doc.get("description", ""),
                "source": doc.get("source", ""),
                "npxCommand": doc.get("npxCommand", ""),
                "activatedAt": doc.get("activatedAt", ""),
            }
            for doc in skills
        ]

    async def get_skill(self, name: str) -> dict | None:
        """Read a single skill, or *None* if it doesn't exist."""
        if self._user_id not in self._store:
            return None
        doc = self._store[self._user_id].get(name)
        if not doc:
            return None
        return {
            "name": doc["name"],
            "description": doc.get("description", ""),
            "source": doc.get("source", ""),
            "npxCommand": doc.get("npxCommand", ""),
            "activatedAt": doc.get("activatedAt", ""),
        }

    async def get_npx_commands(self, skill_ids: list[str]) -> dict[str, str]:
        """Return a mapping of skill name → npxCommand for all requested skills."""
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
