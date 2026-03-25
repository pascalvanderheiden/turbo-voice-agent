"""In-memory skills service.

Drop-in replacement for CosmosSkillsService when Cosmos DB is unavailable.
When ``local_skills_dir`` is set, skill files are persisted to disk so the
Docker-mounted sandbox container picks them up automatically.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"


class InMemorySkillsService:
    """In-memory skill activation management with optional local-disk persistence."""

    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        local_skills_dir: Path | None = None,
    ):
        self._user_id = user_id
        self._store: dict[str, dict[str, dict]] = {}
        self._local_skills_dir = local_skills_dir

    def with_user(self, user_id: str) -> InMemorySkillsService:
        """Return a view of this service scoped to a specific user."""
        return InMemorySkillsService._shared_view(
            self._store, user_id, self._local_skills_dir,
        )

    @classmethod
    def _shared_view(
        cls, store: dict, user_id: str, local_skills_dir: Path | None = None,
    ) -> InMemorySkillsService:
        """Create a new instance that shares the same store but with different user_id."""
        instance = cls(user_id, local_skills_dir=local_skills_dir)
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
        """Remove the skill from in-memory storage and delete local files."""
        if self._user_id in self._store and name in self._store[self._user_id]:
            del self._store[self._user_id][name]
            logger.info("Deactivated skill '%s' for user %s (in-memory)", name, self._user_id)
        else:
            logger.debug("Skill '%s' not found — nothing to deactivate", name)
        self._delete_skill_dir(name)

    async def upload_skill_from_github_to_blob(
        self, skill_name: str, repo: str,
    ) -> list[str]:
        """Download skill files from GitHub (or copy from local project) and write to LOCAL_SKILLS_DIR.

        Falls back to copying from local `.github/skills/` when GitHub download
        fails (e.g. private repo without token, or files not pushed yet).
        """
        if not self._local_skills_dir:
            logger.warning(
                "Blob upload skipped for skill '%s' — no local_skills_dir configured",
                skill_name,
            )
            return []

        # Try GitHub API first
        files_written = await self._download_skill_from_github(skill_name, repo)
        if files_written:
            return files_written

        # Fallback: copy from local project directory
        files_written = self._copy_skill_from_local_project(skill_name)
        if files_written:
            return files_written

        logger.warning(
            "No skill files found for '%s' (tried GitHub + local project)", skill_name,
        )
        return []

    async def _download_skill_from_github(
        self, skill_name: str, repo: str,
    ) -> list[str]:
        """Try downloading skill files from GitHub API."""
        import httpx

        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        files_to_write: list[tuple[str, bytes]] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for dir_path in [
                    f".github/skills/{skill_name}",
                    skill_name,
                    f"skills/{skill_name}",
                ]:
                    try:
                        await self._fetch_github_dir(
                            client, repo, dir_path, dir_path, headers, files_to_write,
                        )
                    except Exception:
                        files_to_write.clear()
                        continue
                    if files_to_write:
                        logger.info(
                            "Found skill '%s' at %s/%s (GitHub)", skill_name, repo, dir_path,
                        )
                        break

            if files_to_write:
                return self.write_skill_files(skill_name, files_to_write)
        except Exception as exc:
            logger.debug("GitHub download for skill '%s' failed: %s", skill_name, exc)
        return []

    def _copy_skill_from_local_project(self, skill_name: str) -> list[str]:
        """Copy skill files from `.github/skills/{name}/` in the project root."""
        # Walk up from local_skills_dir (.agents/skills) to find project root
        project_root = self._local_skills_dir.parent.parent  # .agents/skills -> .agents -> project
        search_paths = [
            project_root / ".github" / "skills" / skill_name,
            project_root / "skills" / skill_name,
        ]
        for src_dir in search_paths:
            if not src_dir.is_dir():
                continue
            files_to_write: list[tuple[str, bytes]] = []
            for file_path in src_dir.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(src_dir)
                    files_to_write.append((str(rel), file_path.read_bytes()))
            if files_to_write:
                logger.info(
                    "Copying skill '%s' from local project: %s (%d files)",
                    skill_name, src_dir, len(files_to_write),
                )
                return self.write_skill_files(skill_name, files_to_write)
        return []

    # ── Local filesystem helpers ──────────────────────────────────────

    def write_skill_files(
        self, skill_name: str, files: list[tuple[str, bytes]],
    ) -> list[str]:
        """Write skill files to ``local_skills_dir/{skill_name}/``.

        Args:
            skill_name: Directory name under local_skills_dir.
            files: List of (relative_path, content) tuples.

        Returns:
            List of written file paths (relative to local_skills_dir).
        """
        if not self._local_skills_dir:
            return []
        skill_dir = self._local_skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "write_skill_files: skill=%s, target_dir=%s, file_count=%d",
            skill_name, skill_dir, len(files),
        )
        written: list[str] = []
        for rel_path, content in files:
            dest = skill_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            written.append(f"{skill_name}/{rel_path}")
            logger.info("Wrote local skill file: %s (%d bytes)", dest, len(content))
        return written

    def _delete_skill_dir(self, skill_name: str) -> None:
        """Remove a skill directory from local_skills_dir (best-effort)."""
        if not self._local_skills_dir:
            return
        skill_dir = self._local_skills_dir / skill_name
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir, ignore_errors=True)
            logger.info("Deleted local skill directory: %s", skill_dir)

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
