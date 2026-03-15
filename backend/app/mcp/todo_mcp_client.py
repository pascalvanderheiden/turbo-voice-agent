"""Microsoft To-Do MCP client — communicates with the MCP server process."""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Seed data for local development
_SEED_TASKS: list[dict[str, Any]] = [
    {
        "id": "task-001",
        "title": "Review design mockups for v2",
        "isCompleted": False,
        "dueDate": "2026-03-20",
        "notes": "Check the latest UX designs from the Figma board",
    },
    {
        "id": "task-002",
        "title": "Prepare sprint demo presentation",
        "isCompleted": True,
        "dueDate": "2026-03-14",
        "notes": "Include architecture diagram and live demo",
    },
    {
        "id": "task-003",
        "title": "Update API documentation",
        "isCompleted": False,
        "dueDate": "2026-03-18",
        "notes": "Add new sandbox endpoints and auth flow",
    },
    {
        "id": "task-004",
        "title": "Fix CI pipeline flaky tests",
        "isCompleted": False,
        "dueDate": None,
        "notes": "",
    },
]


class TodoMcpClient:
    """Client that invokes tools on the Microsoft To-Do MCP server.

    In production the MCP server is a sidecar process speaking JSON-RPC over stdio.
    This implementation wraps tool calls so the TodoAgent stays decoupled from the
    transport layer.  A ``user_token`` is passed per-request so the MCP server can
    act on behalf of the authenticated user.
    """

    def __init__(self) -> None:
        self._healthy = True
        self._stub_tasks: dict[str, dict[str, Any]] = {t["id"]: dict(t) for t in _SEED_TASKS}

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    async def health_check(self) -> bool:
        """Ping the MCP server to verify it is running."""
        # TODO: implement real MCP server health check via JSON-RPC
        return self._healthy

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_token: str | None = None,
    ) -> dict[str, Any]:
        """Invoke a tool on the Microsoft To-Do MCP server.

        Parameters
        ----------
        tool_name:
            MCP tool name, e.g. ``"create_task"``, ``"list_tasks"``.
        arguments:
            Tool arguments as a dict.
        user_token:
            The user's Microsoft OAuth refresh/access token for delegated access.

        Returns
        -------
        dict with the tool result or an ``{"error": ...}`` payload.
        """
        if not user_token:
            return {
                "error": "Microsoft To-Do is not connected. "
                "Please authenticate in your profile settings."
            }

        logger.info("MCP call_tool: %s (has_token=%s)", tool_name, bool(user_token))

        # TODO: Replace stub with real MCP JSON-RPC stdio transport.
        return await self._stub_call(tool_name, arguments)

    # ------------------------------------------------------------------
    # Stub implementation (to be replaced by real MCP transport)
    # ------------------------------------------------------------------

    async def _stub_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Stub with persistent in-memory task store for local dev/testing."""
        if tool_name == "list_tasks":
            return {"tasks": list(self._stub_tasks.values())}

        if tool_name == "create_task":
            task_id = f"task-{uuid.uuid4().hex[:8]}"
            new_task = {
                "id": task_id,
                "title": arguments.get("title", "Untitled"),
                "isCompleted": False,
                "dueDate": arguments.get("dueDate"),
                "notes": arguments.get("notes", ""),
            }
            self._stub_tasks[task_id] = new_task
            return {"task": new_task}

        if tool_name == "get_task":
            task_id = arguments.get("task_id", "unknown")
            task = self._stub_tasks.get(task_id)
            if task:
                return {"task": task}
            return {"error": f"Task {task_id} not found"}

        if tool_name == "update_task":
            task_id = arguments.get("task_id", "unknown")
            task = self._stub_tasks.get(task_id)
            if not task:
                return {"error": f"Task {task_id} not found"}
            for key in ("title", "notes", "dueDate", "isCompleted"):
                if key in arguments:
                    task[key] = arguments[key]
            return {"task": task}

        if tool_name == "delete_task":
            task_id = arguments.get("task_id", "unknown")
            self._stub_tasks.pop(task_id, None)
            return {"success": True}

        return {"error": f"Unknown MCP tool: {tool_name}"}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the MCP server subprocess (no-op until wired)."""
        logger.info("TodoMcpClient: start (stub — MCP server not yet connected)")
        self._healthy = True

    async def stop(self) -> None:
        """Stop the MCP server subprocess."""
        logger.info("TodoMcpClient: stop")
        self._healthy = False
