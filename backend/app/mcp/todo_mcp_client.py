"""Microsoft To-Do MCP client — calls Microsoft Graph API for task management."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Seed data for local development (AUTH_DISABLED mode only)
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

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class TodoMcpClient:
    """Client that manages Microsoft To-Do tasks via Microsoft Graph API.

    When a real user token (refresh token) is provided, it exchanges it for
    an access token and calls the Graph API.  When ``user_token`` is a mock
    value (local dev), falls back to an in-memory stub.
    """

    def __init__(self) -> None:
        self._healthy = True
        self._stub_tasks: dict[str, dict[str, Any]] = {t["id"]: dict(t) for t in _SEED_TASKS}
        import os
        self._client_id = os.environ.get("TODO_OAUTH_CLIENT_ID") or os.environ.get(
            "ENTRA_CLIENT_ID", ""
        )
        self._client_secret = os.environ.get("ENTRA_CLIENT_SECRET", "")
        self._tenant_id = os.environ.get("TODO_OAUTH_TENANT_ID", "common")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    async def health_check(self) -> bool:
        return self._healthy

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def _get_access_token(self, refresh_token: str) -> str | None:
        """Exchange a refresh token for a fresh access token."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "scope": "offline_access Tasks.ReadWrite",
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("Token refresh failed (%d): %s", resp.status, body)
                        return None
                    tokens = await resp.json()
                    return tokens.get("access_token")
        except Exception:
            logger.exception("Token refresh request failed")
            return None

    async def _graph_get(self, access_token: str, path: str) -> dict[str, Any]:
        """GET request to Microsoft Graph API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    return {"error": f"Graph API error ({resp.status}): {body}"}
                return await resp.json()

    async def _graph_post(
        self, access_token: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """POST request to Microsoft Graph API."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GRAPH_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status not in (200, 201):
                    body_text = await resp.text()
                    return {"error": f"Graph API error ({resp.status}): {body_text}"}
                return await resp.json()

    async def _graph_patch(
        self, access_token: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """PATCH request to Microsoft Graph API."""
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{GRAPH_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body_text = await resp.text()
                    return {"error": f"Graph API error ({resp.status}): {body_text}"}
                return await resp.json()

    async def _graph_delete(self, access_token: str, path: str) -> dict[str, Any]:
        """DELETE request to Microsoft Graph API."""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 204:
                    return {"success": True}
                body_text = await resp.text()
                return {"error": f"Graph API error ({resp.status}): {body_text}"}

    # ------------------------------------------------------------------
    # Graph task helpers
    # ------------------------------------------------------------------

    def _normalize_task(self, graph_task: dict[str, Any]) -> dict[str, Any]:
        """Convert a Microsoft Graph task object to our normalized format."""
        due = graph_task.get("dueDateTime")
        return {
            "id": graph_task["id"],
            "title": graph_task.get("title", ""),
            "isCompleted": graph_task.get("status") == "completed",
            "dueDate": due.get("dateTime", "")[:10] if due else None,
            "notes": (graph_task.get("body") or {}).get("content", ""),
        }

    async def _get_default_list_id(self, access_token: str) -> str | None:
        """Get the user's default (Tasks) list ID."""
        result = await self._graph_get(access_token, "/me/todo/lists")
        if "error" in result:
            logger.error("Failed to get todo lists: %s", result["error"])
            return None
        lists = result.get("value", [])
        # Prefer the "defaultList" or the first list
        for lst in lists:
            if lst.get("isOwner") and lst.get("wellknownListName") == "defaultList":
                return lst["id"]
        return lists[0]["id"] if lists else None

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_token: str | None = None,
    ) -> dict[str, Any]:
        if not user_token:
            return {
                "error": "Microsoft To-Do is not connected. "
                "Please authenticate in your profile settings."
            }

        logger.info("MCP call_tool: %s (has_token=%s)", tool_name, bool(user_token))

        # Local dev mock mode
        if user_token == "mock-token-auth-disabled":
            return await self._stub_call(tool_name, arguments)

        # Real Graph API mode
        access_token = await self._get_access_token(user_token)
        if not access_token:
            return {"error": "Failed to refresh access token. Please reconnect Microsoft To-Do."}

        return await self._graph_call(tool_name, arguments, access_token)

    # ------------------------------------------------------------------
    # Real Graph API implementation
    # ------------------------------------------------------------------

    async def _graph_call(
        self, tool_name: str, arguments: dict[str, Any], access_token: str
    ) -> dict[str, Any]:
        """Execute a tool call against the real Microsoft Graph API."""
        list_id = await self._get_default_list_id(access_token)
        if not list_id:
            return {"error": "Could not find your default To-Do list."}

        base_path = f"/me/todo/lists/{list_id}/tasks"

        if tool_name == "list_tasks":
            result = await self._graph_get(
                access_token, f"{base_path}?$top=50&$orderby=createdDateTime desc"
            )
            if "error" in result:
                return result
            tasks = [self._normalize_task(t) for t in result.get("value", [])]
            return {"tasks": tasks}

        if tool_name == "create_task":
            body: dict[str, Any] = {"title": arguments.get("title", "Untitled")}
            if arguments.get("notes"):
                body["body"] = {"content": arguments["notes"], "contentType": "text"}
            if arguments.get("dueDate"):
                body["dueDateTime"] = {
                    "dateTime": f"{arguments['dueDate']}T00:00:00",
                    "timeZone": "UTC",
                }
            logger.info("Graph create_task: POST %s body=%s", base_path, body)
            result = await self._graph_post(access_token, base_path, body)
            if "error" in result:
                logger.error("Graph create_task failed: %s", result["error"])
                return result
            return {"task": self._normalize_task(result)}

        if tool_name == "get_task":
            task_id = arguments.get("task_id", "")
            result = await self._graph_get(access_token, f"{base_path}/{task_id}")
            if "error" in result:
                return result
            return {"task": self._normalize_task(result)}

        if tool_name == "update_task":
            task_id = arguments.get("task_id", "")
            body = {}
            if "title" in arguments:
                body["title"] = arguments["title"]
            if "notes" in arguments:
                body["body"] = {"content": arguments["notes"], "contentType": "text"}
            if "dueDate" in arguments:
                body["dueDateTime"] = {
                    "dateTime": f"{arguments['dueDate']}T00:00:00",
                    "timeZone": "UTC",
                }
            if "isCompleted" in arguments:
                body["status"] = "completed" if arguments["isCompleted"] else "notStarted"
            result = await self._graph_patch(access_token, f"{base_path}/{task_id}", body)
            if "error" in result:
                return result
            return {"task": self._normalize_task(result)}

        if tool_name == "delete_task":
            task_id = arguments.get("task_id", "")
            return await self._graph_delete(access_token, f"{base_path}/{task_id}")

        return {"error": f"Unknown tool: {tool_name}"}

    # ------------------------------------------------------------------
    # Stub implementation (local dev with AUTH_DISABLED)
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
        logger.info("TodoMcpClient: started (Graph API mode)")
        self._healthy = True

    async def stop(self) -> None:
        logger.info("TodoMcpClient: stop")
        self._healthy = False
