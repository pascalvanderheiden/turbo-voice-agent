"""Skills Agent — specialist agent for managing installed and marketplace skills."""

import json
import logging

from app.services.skills_service import SkillsService

logger = logging.getLogger(__name__)


class SkillsAgent:
    """Agent that handles skill installation, uninstallation, search, and listing."""

    def __init__(self, skills_service: SkillsService):
        self._service = skills_service

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_skills",
                    "description": "List all installed agent skills with their metadata",
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
                    "name": "install_skill",
                    "description": "Install a skill from the skills.sh marketplace (e.g. repo='vercel-labs/skills', name='find-skills')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "GitHub repo (owner/repo) containing the skill"},
                            "skill_name": {"type": "string", "description": "Name of the skill to install"},
                        },
                        "required": ["repo", "skill_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "uninstall_skill",
                    "description": "Uninstall (delete) an installed skill by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the skill to uninstall"},
                        },
                        "required": ["name"],
                    },
                },
            },
        ]

    async def handle_function_call(self, function_name: str, arguments: str) -> str:
        """Execute a function call and return the result as JSON string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        if function_name == "list_skills":
            skills = self._service.list_installed()
            return json.dumps({"skills": skills, "count": len(skills)})

        elif function_name == "search_skills":
            results = await self._service.search_marketplace(args.get("query", ""))
            return json.dumps({"results": results, "count": len(results)})

        elif function_name == "install_skill":
            result = await self._service.install_from_marketplace(
                args["repo"], args["skill_name"]
            )
            return json.dumps(result)

        elif function_name == "uninstall_skill":
            result = self._service.uninstall(args["name"])
            return json.dumps(result)

        return json.dumps({"error": f"Unknown function: {function_name}"})
