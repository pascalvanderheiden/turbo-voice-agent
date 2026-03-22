"""Work Agent — specialist agent for Microsoft 365 workplace intelligence via WorkIQ."""

import json
import logging
from typing import Any

from app.mcp.work_mcp_client import WorkMcpClient

logger = logging.getLogger(__name__)

WORK_AGENT_INSTRUCTIONS = """You are the Work Agent. You answer questions about the user's
work environment — emails, meetings, documents, Teams messages, and people information
using Microsoft 365 data via WorkIQ.

When the user asks about work-related topics (meetings, emails, documents, colleagues),
use the ask_work_question tool. Summarize the response concisely — your responses will
be spoken aloud by a voice agent."""


class WorkAgent:
    """Agent that answers workplace questions by delegating to the WorkIQ MCP server."""

    def __init__(self, mcp_client: WorkMcpClient, get_user_token: Any = None):
        self._mcp = mcp_client
        self._get_user_token = get_user_token

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "ask_work_question",
                    "description": (
                        "Ask a question about the user's work environment — emails, "
                        "meetings, documents, Teams messages, and people information "
                        "from Microsoft 365"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The work-related question to ask",
                            },
                            "file_urls": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional OneDrive or SharePoint file URLs for context",
                            },
                        },
                        "required": ["question"],
                    },
                },
            },
        ]

    async def _get_token(self, user_id: str) -> str | None:
        """Retrieve the user's Work Account OAuth token."""
        if self._get_user_token:
            return await self._get_user_token(user_id)
        return None

    async def handle_function_call(
        self, function_name: str, arguments: str, user_id: str = "default-user"
    ) -> str:
        """Execute a function call and return the result as a JSON string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        token = await self._get_token(user_id)
        if not token:
            return json.dumps({
                "error": "Work account is not connected. "
                "Please connect your Microsoft work account in Settings."
            })

        if function_name == "ask_work_question":
            question = args.get("question", "")
            file_urls = args.get("file_urls")
            result = await self._mcp.ask(
                question=question,
                user_token=token,
                file_urls=file_urls,
            )
            if "error" in result:
                return json.dumps(result)
            return json.dumps({
                "success": True,
                "answer": result.get("response", ""),
                "conversationId": result.get("conversationId", ""),
            })

        return json.dumps({"error": f"Unknown function: {function_name}"})
