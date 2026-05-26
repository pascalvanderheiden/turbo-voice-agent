"""Sandbox management REST API routes."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.dev_agent import _active_sandbox_tasks
from app.models.sandbox import SandboxConfig
from app.services.session_sandbox_client import get_sandbox_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

_sandbox_service = None

# Admin/global identifier for routes that don't target a specific dev task.
# With LocalSandboxClient the identifier is ignored; with SessionSandboxClient
# this allocates a dedicated "admin" session for health checks and task listing.
_ADMIN_IDENTIFIER = "admin"

# Persistent premium-request tracking:
# The sandbox reports a running count that resets on container restart.
# We track the last value we saw and accumulate a baseline so the total
# is never lost when the sandbox restarts or tasks are deleted.
_premium_baseline: int = 0      # accumulated from previous sandbox lifecycles
_last_sandbox_premium: int = 0  # last value seen from the sandbox /health


def set_sandbox_service(service) -> None:
    global _sandbox_service
    _sandbox_service = service


def _get_service():
    if _sandbox_service is None:
        raise HTTPException(status_code=503, detail="Sandbox service unavailable")
    return _sandbox_service


async def _probe_sandbox_health() -> tuple[bool, int, int]:
    """Probe sandbox /health and return (reachable, activeTasks, premiumRequests).

    premiumRequests is a cumulative total that survives sandbox restarts:
    if the sandbox counter drops (restart), we fold the previous value
    into a baseline so nothing is lost.
    """
    global _premium_baseline, _last_sandbox_premium
    try:
        client = get_sandbox_client()
        resp = await client.request(
            "GET", "/health", identifier=_ADMIN_IDENTIFIER, timeout=5.0,
        )
        data = resp.json()
        active = data.get("activeTasks", 0)
        sandbox_premium = data.get("premiumRequests", 0)

        # Detect sandbox restart: its counter dropped below what we last saw
        if sandbox_premium < _last_sandbox_premium:
            _premium_baseline += _last_sandbox_premium
        _last_sandbox_premium = sandbox_premium

        total_premium = _premium_baseline + sandbox_premium
        return True, active, total_premium
    except Exception:
        return False, 0, _premium_baseline + _last_sandbox_premium


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

    # Fallback: check Cosmos profile if in-memory cache is empty (e.g. after restart)
    if not github_connected:
        profile_svc = getattr(request.app.state, "user_profile_service", None)
        if profile_svc:
            try:
                profile = await profile_svc.get_profile(user_id)
                if profile and profile.get("githubSandboxToken"):
                    _connection_store[f"sandbox:{user_id}"] = {
                        "token": profile["githubSandboxToken"],
                        "connectedAt": profile.get("githubSandboxConnectedAt", ""),
                    }
                    github_connected = True
            except Exception:
                pass

    # Restore premium baseline from Cosmos on first request after deploy
    global _premium_baseline, _last_sandbox_premium
    profile_svc = getattr(request.app.state, "user_profile_service", None)
    if profile_svc and _premium_baseline == 0 and _last_sandbox_premium == 0:
        try:
            usage = await profile_svc.get_premium_usage(user_id)
            stored_total = usage.get("total", 0)
            if stored_total > premium_requests:
                _premium_baseline = stored_total - _last_sandbox_premium
                premium_requests = _premium_baseline + _last_sandbox_premium
        except Exception:
            pass

    # Persist premium count to profile (async, non-blocking)
    if profile_svc and premium_requests > 0:
        try:
            await profile_svc.record_premium_usage(user_id, premium_requests)
        except Exception:
            pass

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

    # Use backend pipeline count (not sandbox internal count)
    from app.routes.dev import _running_pipelines

    active_pipeline_count = len(_running_pipelines)
    result["activeTasks"] = active_pipeline_count
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


@router.post("/stop")
async def stop_sandbox(request: Request):
    """Stop all active sandbox tasks and cancel running pipelines."""
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("Sandbox stop requested for user %s", user_id)

    # Cancel all running backend pipeline asyncio tasks
    from app.routes.dev import _get_service as _get_dev_service
    from app.routes.dev import _running_pipelines
    cancelled = 0
    for tid, atask in list(_running_pipelines.items()):
        if not atask.done():
            atask.cancel()
            cancelled += 1
            # Mark the dev task as failed so it doesn't look "running"
            try:
                svc = _get_dev_service().with_user(user_id)
                await svc.set_status(tid, "failed")
            except Exception:
                pass
    _running_pipelines.clear()
    logger.info("Cancelled %d pipeline tasks", cancelled)

    # Kill all active sandbox container tasks
    # NOTE: Listing global tasks via /tasks is admin-style behavior — primarily
    # meaningful in local-dev (single shared sandbox). In session-pool mode each
    # task lives in its own session; the per-task DELETE in cancel_sandbox_task_for
    # is the canonical cleanup path.
    killed = 0
    try:
        client = get_sandbox_client()
        resp = await client.request(
            "GET", "/tasks", identifier=_ADMIN_IDENTIFIER, timeout=10.0,
        )
        data = resp.json()
        for t in data.get("tasks", []):
            tid = t.get("id")
            if tid and t.get("exitCode") is None:
                try:
                    await client.request(
                        "DELETE",
                        f"/tasks/{tid}",
                        identifier=_ADMIN_IDENTIFIER,
                        timeout=10.0,
                    )
                    killed += 1
                except Exception:
                    pass
    except Exception as exc:
        logger.warning("Failed to stop sandbox tasks: %s", exc)

    _active_sandbox_tasks.clear()
    return {"stopped": True, "killedTasks": killed, "cancelledPipelines": cancelled}


@router.post("/start")
async def start_sandbox(request: Request):
    """Start/restart the sandbox environment.

    Local dev: starts the docker-compose sandbox container (idempotent — if
    already healthy, returns immediately as "ready").
    Session-pool mode: pool is always live; this is best-effort health probe
    only — there is no per-user "start" operation for shared session pools.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    logger.info("Sandbox start requested for user %s", user_id)

    # Local dev path: actually start the docker container.
    docker_svc = getattr(request.app.state, "docker_sandbox_svc", None)
    if docker_svc is not None:
        await svc.set_status("provisioning")
        healthy = await docker_svc.start()
        if healthy:
            await svc.set_status("ready")
            return {"status": "ready", "message": "Local sandbox started"}
        await svc.set_status("stopped")
        raise HTTPException(
            status_code=503,
            detail=(
                "Failed to start local sandbox. Ensure Docker is running, then "
                "try 'docker compose up -d sandbox' manually."
            ),
        )

    # Session-pool path: nothing to start — the pool is always live.
    # Probe health so the response reflects reality instead of a stale "provisioning".
    reachable, _, _ = await _probe_sandbox_health()
    live = "ready" if reachable else "stopped"
    await svc.set_status(live)
    return {
        "status": live,
        "message": (
            "Session pool is live — no per-user start required."
            if reachable
            else "Session pool unreachable. Check backend logs and Azure deployment."
        ),
    }


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
        client = get_sandbox_client()
        resp = await client.request(
            "POST",
            "/tasks",
            identifier=body.devTaskId,
            json={"command": body.command, "args": body.args},
            timeout=30.0,
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
            client = get_sandbox_client()
            async with client.stream_response(
                "GET",
                f"/tasks/{task_id}/stream",
                identifier=task_id,
                timeout=httpx.Timeout(10.0, read=None),
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        yield f"{line}\n\n"
        except httpx.HTTPError as exc:
            logger.error("Sandbox SSE stream error: %s", exc)
            yield 'data: {"type": "error", "message": "Sandbox connection lost"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
