"""Microsoft To-Do MCP client — communicates with the MCP server process."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TodoMcpClient:
    """Client that invokes tools on the Microsoft To-Do MCP server.

    In production the MCP server is a sidecar process speaking JSON-RPC over stdio.
    This implementation wraps tool calls so the TodoAgent stays decoupled from the
    transport layer.  A ``user_token`` is passed per-request so the MCP server can
    act on behalf of the authenticated user.
    """

    def __init__(self) -> None:
        self._healthy = True

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
        #       The MCP server will be started as a subprocess in main.py lifespan
        #       and this client will send JSON-RPC requests over stdin/stdout.
        #
        # For now, return a placeholder response so the full wiring can be tested
        # end-to-end before the MCP server is actually connected.
        return await self._stub_call(tool_name, arguments)

    # ------------------------------------------------------------------
    # Stub implementation (to be replaced by real MCP transport)
    # ------------------------------------------------------------------

    async def _stub_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Stub that returns plausible responses for development/testing."""
        if tool_name == "list_tasks":
            return {"tasks": []}
        if tool_name == "create_task":
            return {
                "task": {
                    "id": "stub-task-id",
                    "title": arguments.get("title", "Untitled"),
                    "isCompleted": False,
                    "dueDate": arguments.get("dueDate"),
                    "notes": arguments.get("notes", ""),
                },
            }
        if tool_name == "get_task":
            return {
                "task": {
                    "id": arguments.get("task_id", "unknown"),
                    "title": "Stub task",
                    "isCompleted": False,
                    "notes": "",
                },
            }
        if tool_name == "update_task":
            return {"task": {"id": arguments.get("task_id", "unknown"), **arguments}}
        if tool_name == "delete_task":
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
