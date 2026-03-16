"""Sandbox management REST API routes."""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models.sandbox import SandboxConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

_sandbox_service = None

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")


def set_sandbox_service(service) -> None:
    global _sandbox_service
    _sandbox_service = service


def _get_service():
    if _sandbox_service is None:
        raise HTTPException(status_code=503, detail="Sandbox service unavailable")
    return _sandbox_service


async def _probe_sandbox_health() -> tuple[bool, int, int]:
    """Probe sandbox /health and return (reachable, activeTasks, premiumRequests)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{SANDBOX_URL}/health")
            data = resp.json()
            active = data.get("activeTasks", 0)
            premium = data.get("premiumRequests", 0)
            return True, active, premium
    except Exception:
        return False, 0, 0


@router.get("/status")
async def get_sandbox_status(request: Request):
    """Get sandbox status for the current user, enriched with live health check."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    state = await svc.get_state()

    reachable, active_tasks, premium_requests = await _probe_sandbox_health()
    live_status = "ready" if reachable else "stopped"

    # Check if user has a GitHub token stored in user connections
    from app.routes.user import _connection_store

    github_connected = bool(_connection_store.get(f"sandbox:{user_id}"))

    if state is None:
        return {
            "status": live_status,
            "activeTasks": active_tasks,
            "premiumRequests": premium_requests,
            "githubConnected": github_connected,
            "config": SandboxConfig().model_dump(),
        }

    result = state if isinstance(state, dict) else state.model_dump()
    result["status"] = live_status
    result["activeTasks"] = active_tasks
    result["premiumRequests"] = premium_requests
    result["githubConnected"] = github_connected
    return result


class UpdateConfigRequest(BaseModel):
    model: str | None = None


@router.put("/config")
async def update_sandbox_config(body: UpdateConfigRequest, request: Request):
    """Update sandbox configuration (e.g., default model)."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    config = SandboxConfig(model=body.model or "claude-opus-4.6")
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
    """Submit a task to the sandbox container for execution."""
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("Sandbox task created for user %s: %s %s", user_id, body.command, body.args)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SANDBOX_URL}/tasks",
                json={"command": body.command, "args": body.args},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "taskId": data.get("id", f"stask-{body.devTaskId}"),
                "status": "submitted",
                "command": body.command,
                "args": body.args,
            }
    except httpx.HTTPError as exc:
        logger.error("Failed to submit task to sandbox: %s", exc)
        raise HTTPException(status_code=502, detail="Sandbox unreachable") from exc


@router.get("/tasks/{task_id}/stream")
async def stream_sandbox_task(task_id: str, request: Request):
    """Proxy SSE stream from sandbox container."""
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("SSE stream requested for sandbox task %s (user=%s)", task_id, user_id)

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET", f"{SANDBOX_URL}/tasks/{task_id}/stream"
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except httpx.HTTPError as exc:
            logger.error("Sandbox SSE stream error: %s", exc)
            yield 'data: {"type": "error", "message": "Sandbox connection lost"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")
