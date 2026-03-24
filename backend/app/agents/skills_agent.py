"""Skills Agent — specialist agent for managing activated and marketplace skills."""

import json
import logging
from collections.abc import Awaitable, Callable

from app.services.cosmos_skills_service import CosmosSkillsService
from app.services.skills_service import SkillsService

logger = logging.getLogger(__name__)


class SkillsAgent:
    """Agent that handles skill activation, deactivation, search, and listing."""

    def __init__(
        self,
        skills_service: SkillsService,
        cosmos_skills: CosmosSkillsService | None = None,
        sync_sandbox: Callable[[], Awaitable[dict | None]] | None = None,
        delete_sandbox_skill: Callable[[str], Awaitable[dict | None]] | None = None,
    ):
        self._service = skills_service
        self._cosmos_skills = cosmos_skills
        self._sync_sandbox = sync_sandbox
        self._delete_sandbox_skill = delete_sandbox_skill

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_skills",
                    "description": "List all activated agent skills",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_skills",
                    "description": "Search the skills.sh marketplace for available skills",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query for the marketplace"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "activate_skill",
                    "description": "Activate a skill from the skills.sh marketplace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "GitHub repo (owner/repo) containing the skill"},
                            "skill_name": {"type": "string", "description": "Name of the skill to activate"},
                            "description": {"type": "string", "description": "Skill description"},
                        },
                        "required": ["repo", "skill_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "deactivate_skill",
                    "description": "Deactivate an activated skill by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the skill to deactivate"},
                        },
                        "required": ["name"],
                    },
                },
            },
        ]

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        """Execute a function call and return the result as JSON string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        if function_name == "list_skills":
            if self._cosmos_skills:
                svc = self._cosmos_skills.with_user(user_id)
                skills = await svc.list_activated()
                return json.dumps({"skills": skills, "count": len(skills)})
            return json.dumps({"skills": [], "count": 0})

        elif function_name == "search_skills":
            results = await self._service.search_marketplace(args.get("query", ""))
            return json.dumps({"results": results, "count": len(results)})

        elif function_name == "activate_skill":
            if not self._cosmos_skills:
                return json.dumps({"error": "Skills service not available"})
            svc = self._cosmos_skills.with_user(user_id)
            repo = args["repo"]
            skill_name = args["skill_name"]
            desc = args.get("description", "")
            is_local = repo == "local"
            npx_cmd = (
                "__local__" if is_local
                else f"npx -y degit {repo}/{skill_name} .github/skills/{skill_name}"
            )
            result = await svc.activate_skill(skill_name, desc, repo, npx_cmd)

            # For marketplace skills, download from GitHub → blob storage
            blob_uploaded = 0
            if not is_local and repo:
                uploaded = await svc.upload_skill_from_github_to_blob(skill_name, repo)
                if uploaded:
                    blob_uploaded = len(uploaded)
                    # Mark as blob-stored so runtime treats it like a local skill
                    await svc.activate_skill(skill_name, desc, repo, "__local__")
                    logger.info(
                        "Marketplace skill '%s' uploaded to blob (%d files)",
                        skill_name, blob_uploaded,
                    )

            # Hot-reload: push to running sandbox
            if self._sync_sandbox:
                await self._sync_sandbox()

            return json.dumps({
                "name": result["name"], "success": True, "blobFiles": blob_uploaded,
            })

        elif function_name == "deactivate_skill":
            if not self._cosmos_skills:
                return json.dumps({"error": "Skills service not available"})
            svc = self._cosmos_skills.with_user(user_id)
            await svc.deactivate_skill(args["name"])

            # Hot-reload: remove from running sandbox
            if self._delete_sandbox_skill:
                await self._delete_sandbox_skill(args["name"])

            return json.dumps({"name": args["name"], "success": True})

        return json.dumps({"error": f"Unknown function: {function_name}"})
