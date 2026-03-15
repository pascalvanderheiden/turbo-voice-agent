"""Todo Agent — specialist agent for Microsoft To-Do task management via MCP."""

import json
import logging
from typing import Any

from app.mcp.todo_mcp_client import TodoMcpClient

logger = logging.getLogger(__name__)

TODO_AGENT_INSTRUCTIONS = """You are the Todo Agent. You manage to-do tasks for the user
via Microsoft To-Do. You can create, list, read, update, delete, and complete tasks.

When creating a task, confirm the title with the user.
When listing tasks, provide a brief summary of each.
Respond concisely — your responses will be spoken aloud by a voice agent."""


class TodoAgent:
    """Agent that handles to-do operations by delegating to the Microsoft To-Do MCP server."""

    def __init__(self, mcp_client: TodoMcpClient, get_user_token: Any = None):
        self._mcp = mcp_client
        # Callable: async (user_id) -> str | None — retrieves the stored OAuth token
        self._get_user_token = get_user_token

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_todo",
                    "description": "Create a new to-do task in Microsoft To-Do",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The task title"},
                            "notes": {
                                "type": "string",
                                "description": "Optional notes/body for the task",
                            },
                            "dueDate": {
                                "type": "string",
                                "description": "Optional due date in ISO 8601 format",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_todos",
                    "description": "List all to-do tasks from Microsoft To-Do",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_todo",
                    "description": "Get a specific to-do task by its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "The task ID"},
                        },
                        "required": ["todo_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_todo",
                    "description": "Update an existing to-do task's title, notes, or due date",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "The task ID to update"},
                            "title": {"type": "string", "description": "New title (optional)"},
                            "notes": {"type": "string", "description": "New notes (optional)"},
                            "dueDate": {
                                "type": "string",
                                "description": "New due date in ISO 8601 (optional)",
                            },
                        },
                        "required": ["todo_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_todo",
                    "description": "Delete a to-do task by its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "The task ID to delete"},
                        },
                        "required": ["todo_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_todo",
                    "description": "Mark a to-do task as completed or uncompleted",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todo_id": {"type": "string", "description": "The task ID"},
                            "is_completed": {
                                "type": "boolean",
                                "description": "True to mark complete, false to mark incomplete",
                            },
                        },
                        "required": ["todo_id"],
                    },
                },
            },
        ]

    async def _get_token(self, user_id: str) -> str | None:
        """Retrieve the user's Microsoft To-Do OAuth token."""
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
            msg = (
                "Microsoft To-Do is not connected. "
                "Please authenticate in your profile settings."
            )
            return json.dumps({"error": msg})

        if function_name == "create_todo":
            result = await self._mcp.call_tool(
                "create_task",
                {
                    "title": args["title"],
                    "notes": args.get("notes", ""),
                    "dueDate": args.get("dueDate"),
                },
                user_token=token,
            )
            if "error" in result:
                return json.dumps(result)
            task = result.get("task", {})
            return json.dumps({"success": True, "todo": task})

        elif function_name == "get_todos":
            result = await self._mcp.call_tool("list_tasks", {}, user_token=token)
            if "error" in result:
                return json.dumps(result)
            return json.dumps({"todos": result.get("tasks", [])})

        elif function_name == "get_todo":
            result = await self._mcp.call_tool(
                "get_task", {"task_id": args["todo_id"]}, user_token=token
            )
            if "error" in result:
                return json.dumps(result)
            return json.dumps({"todo": result.get("task", {})})

        elif function_name == "update_todo":
            update_args: dict[str, Any] = {"task_id": args["todo_id"]}
            if "title" in args:
                update_args["title"] = args["title"]
            if "notes" in args:
                update_args["notes"] = args["notes"]
            if "dueDate" in args:
                update_args["dueDate"] = args["dueDate"]
            result = await self._mcp.call_tool("update_task", update_args, user_token=token)
            if "error" in result:
                return json.dumps(result)
            return json.dumps({"success": True, "todo": result.get("task", {})})

        elif function_name == "delete_todo":
            result = await self._mcp.call_tool(
                "delete_task", {"task_id": args["todo_id"]}, user_token=token
            )
            if "error" in result:
                return json.dumps(result)
            return json.dumps({"success": True})

        elif function_name == "complete_todo":
            is_completed = args.get("is_completed", True)
            result = await self._mcp.call_tool(
                "update_task",
                {"task_id": args["todo_id"], "isCompleted": is_completed},
                user_token=token,
            )
            if "error" in result:
                return json.dumps(result)
            task = result.get("task", {})
            return json.dumps({"success": True, "todo": task})

        return json.dumps({"error": f"Unknown function: {function_name}"})
