"""Todo REST routes — proxy CRUD operations through the TodoAgent to the MCP server."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.agents.todo_agent import TodoAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/todos", tags=["todos"])

_todo_agent: TodoAgent | None = None


def set_todo_agent(agent: TodoAgent) -> None:
    global _todo_agent
    _todo_agent = agent


def _get_agent() -> TodoAgent:
    if _todo_agent is None:
        raise HTTPException(status_code=503, detail="Todo agent unavailable")
    return _todo_agent


async def _check_connection(user_id: str) -> None:
    """Raise 503 if the user hasn't connected Microsoft To-Do."""
    from app.routes.user import get_todo_user_token

    token = await get_todo_user_token(user_id)
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Microsoft To-Do is not connected. "
            "Please authenticate in your profile settings.",
        )


# ── Request models ──────────────────────────────────────────────


class TodoCreate(BaseModel):
    title: str
    notes: str | None = None
    dueDate: str | None = None


class TodoUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    dueDate: str | None = None
    isCompleted: bool | None = None


# ── Routes ──────────────────────────────────────────────────────


@router.get("")
async def list_todos(request: Request):
    """List all to-do tasks from Microsoft To-Do."""
    user_id = getattr(request.state, "user_id", "default-user")
    await _check_connection(user_id)
    agent = _get_agent()
    result_json = await agent.handle_function_call("get_todos", "{}", user_id=user_id)
    result = json.loads(result_json)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result.get("todos", [])


@router.get("/{todo_id}")
async def get_todo(todo_id: str, request: Request):
    """Get a single to-do task by ID."""
    user_id = getattr(request.state, "user_id", "default-user")
    await _check_connection(user_id)
    agent = _get_agent()
    result_json = await agent.handle_function_call(
        "get_todo", json.dumps({"todo_id": todo_id}), user_id=user_id
    )
    result = json.loads(result_json)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result.get("todo", {})


@router.post("", status_code=201)
async def create_todo(data: TodoCreate, request: Request):
    """Create a new to-do task."""
    user_id = getattr(request.state, "user_id", "default-user")
    await _check_connection(user_id)
    agent = _get_agent()
    args = {"title": data.title}
    if data.notes:
        args["notes"] = data.notes
    if data.dueDate:
        args["dueDate"] = data.dueDate
    result_json = await agent.handle_function_call("create_todo", json.dumps(args), user_id=user_id)
    result = json.loads(result_json)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result.get("todo", result)


@router.put("/{todo_id}")
async def update_todo(todo_id: str, data: TodoUpdate, request: Request):
    """Update an existing to-do task."""
    user_id = getattr(request.state, "user_id", "default-user")
    await _check_connection(user_id)
    agent = _get_agent()
    args: dict = {"todo_id": todo_id}
    if data.title is not None:
        args["title"] = data.title
    if data.notes is not None:
        args["notes"] = data.notes
    if data.dueDate is not None:
        args["dueDate"] = data.dueDate
    if data.isCompleted is not None:
        args["isCompleted"] = data.isCompleted

    # If only toggling completion, use complete_todo
    if (
        data.isCompleted is not None
        and data.title is None
        and data.notes is None
        and data.dueDate is None
    ):
        result_json = await agent.handle_function_call(
            "complete_todo",
            json.dumps({"todo_id": todo_id, "is_completed": data.isCompleted}),
            user_id=user_id,
        )
    else:
        result_json = await agent.handle_function_call(
            "update_todo", json.dumps(args), user_id=user_id
        )
    result = json.loads(result_json)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result.get("todo", result)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: str, request: Request):
    """Delete a to-do task."""
    user_id = getattr(request.state, "user_id", "default-user")
    await _check_connection(user_id)
    agent = _get_agent()
    result_json = await agent.handle_function_call(
        "delete_todo", json.dumps({"todo_id": todo_id}), user_id=user_id
    )
    result = json.loads(result_json)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
