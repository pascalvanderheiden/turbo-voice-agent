"""Sandbox management REST API routes."""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models.sandbox import SandboxConfig, SandboxState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

_sandbox_service = None


def set_sandbox_service(service) -> None:
    global _sandbox_service
    _sandbox_service = service


def _get_service():
    if _sandbox_service is None:
        raise HTTPException(status_code=503, detail="Sandbox service unavailable")
    return _sandbox_service


@router.get("/status")
async def get_sandbox_status(request: Request):
    """Get sandbox status for the current user."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    state = await svc.get_state()
    if state is None:
        return {"status": "not_configured", "githubConnected": False, "config": SandboxConfig().model_dump()}
    return state


class UpdateConfigRequest(BaseModel):
    model: str | None = None


@router.put("/config")
async def update_sandbox_config(body: UpdateConfigRequest, request: Request):
    """Update sandbox configuration (e.g., default model)."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    config = SandboxConfig(model=body.model or "claude-sonnet-4")
    state = await svc.update_config(config)
    return state


@router.post("/recreate")
async def recreate_sandbox(request: Request):
    """Recreate the sandbox (e.g., after skill changes)."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    await svc.set_status("provisioning")
    logger.info("Sandbox recreation requested for user %s", user_id)
    return {"status": "provisioning", "message": "Sandbox recreation initiated"}


class SandboxTaskRequest(BaseModel):
    devTaskId: str
    command: str
    args: list[str] = []


@router.post("/tasks")
async def create_sandbox_task(body: SandboxTaskRequest, request: Request):
    """Submit a task to the sandbox for execution."""
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("Sandbox task created for user %s: %s %s", user_id, body.command, body.args)
    # TODO: delegate to actual sandbox Container App
    return {
        "taskId": f"stask-{body.devTaskId}",
        "status": "submitted",
        "command": body.command,
        "args": body.args,
    }


@router.get("/tasks/{task_id}/stream")
async def stream_sandbox_task(task_id: str, request: Request):
    """Stream sandbox task output via SSE."""
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("SSE stream requested for sandbox task %s (user=%s)", task_id, user_id)

    async def event_stream():
        # TODO: proxy actual sandbox SSE stream
        yield f"data: {{\"type\": \"start\", \"taskId\": \"{task_id}\"}}\n\n"
        yield f"data: {{\"type\": \"output\", \"text\": \"Sandbox task {task_id} started...\"}}\n\n"
        yield f"data: {{\"type\": \"complete\", \"taskId\": \"{task_id}\"}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
