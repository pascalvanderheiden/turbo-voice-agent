"""Development Task REST API routes."""

import asyncio
import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.agents.dev_agent import cancel_sandbox_task_for
from app.models.dev_task import DevTask, DevTaskCreate
from app.services.dev_service import InMemoryDevService

logger = logging.getLogger(__name__)

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")
USE_ACI_SANDBOX = os.getenv("USE_ACI_SANDBOX", "").lower() == "true"


def _resolve_sandbox_url(task_id: str = "") -> str:
    """Resolve sandbox URL — per-task ACI or static Container App."""
    if USE_ACI_SANDBOX and _dev_agent and hasattr(_dev_agent, "_aci_sandbox_service"):
        svc = _dev_agent._aci_sandbox_service
        if svc:
            url = svc.get_sandbox_url(task_id)
            if url:
                return url
    return SANDBOX_URL

router = APIRouter(prefix="/api/dev", tags=["development"])

_dev_service: InMemoryDevService | None = None
_pipeline_fn = None
_skills_service = None
_cosmos_skills = None
_spec_service = None
_dev_agent = None

# Track running pipeline asyncio tasks so they can be cancelled on delete
_running_pipelines: dict[str, asyncio.Task] = {}  # task_id → asyncio.Task

# Track live preview server processes
_live_previews: dict[str, dict] = {}  # task_id → {url, sandbox_task_id}


async def _restart_dev_server(task_id: str, mode: str) -> dict:
    """Restart a dev server in the sandbox from existing workspace files.

    Checks the workspace directory exists, discovers the actual project
    subdirectory (slides use a deckio subfolder), starts the right dev
    server command, polls for health, and registers in _live_previews.
    """
    sandbox_url = _resolve_sandbox_url(task_id)
    base_dir = f"/workspace/{task_id}"

    # 1. Verify workspace exists and discover project directory
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            probe = await client.post(
                f"{sandbox_url}/tasks",
                json={"command": "ls -1", "args": [], "workDir": base_dir},
            )
            if probe.status_code >= 400:
                raise HTTPException(
                    status_code=410,
                    detail=(
                        f"Workspace for task {task_id} not found in sandbox. "
                        "The container may have been restarted."
                    ),
                )
            probe_id = probe.json().get("id")
            # Give ls a moment to complete, then read output
            await asyncio.sleep(2)
            status_resp = await client.get(f"{sandbox_url}/tasks/{probe_id}/status")
            ls_output = ""
            if status_resp.status_code == 200:
                for entry in status_resp.json().get("recentOutput", []):
                    ls_output += entry.get("data", "")
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail="Cannot reach sandbox — it may be stopped or restarting.",
        )

    if not ls_output.strip():
        raise HTTPException(
            status_code=410,
            detail="Workspace directory is empty or missing.",
        )

    # For slides: the deckio project lives in a subdirectory (e.g. slidedeck-xxx/)
    # Find the subdir that contains package.json by looking for it
    if mode == "slides":
        work_dir = base_dir
        # Check if package.json is in a subdirectory
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                find_resp = await client.post(
                    f"{sandbox_url}/tasks",
                    json={
                        "command": (
                            "find . -maxdepth 2 -name package.json"
                            " -not -path '*/node_modules/*' | head -1"
                        ),
                        "args": [],
                        "workDir": base_dir,
                    },
                )
                if find_resp.status_code < 300:
                    find_id = find_resp.json().get("id")
                    await asyncio.sleep(2)
                    find_status = await client.get(
                        f"{sandbox_url}/tasks/{find_id}/status"
                    )
                    if find_status.status_code == 200:
                        find_out = ""
                        for entry in find_status.json().get("recentOutput", []):
                            find_out += entry.get("data", "")
                        pkg_path = find_out.strip()
                        if pkg_path and pkg_path != "./package.json":
                            # e.g. "./slidedeck-xxx/package.json" → use that dir
                            subdir = pkg_path.rsplit("/", 1)[0]
                            work_dir = f"{base_dir}/{subdir.lstrip('./')}"
                            logger.info(
                                "Slides project found in subdir: %s", work_dir
                            )
        except Exception:
            pass  # Fall back to base_dir
    else:
        work_dir = base_dir

    # 2. Pick port and commands based on mode
    if mode == "slides":
        port = 3333
        strategies = [
            (f"cd {work_dir} && npm run dev -- --port 3333 --host", 3333),
        ]
    else:
        port = 3000
        strategies = [
            (
                f"cd {work_dir} && npm install --legacy-peer-deps 2>/dev/null"
                f" && npm run dev -- --port 3000 --host",
                3000,
            ),
            (f"npx --yes serve {work_dir} -l 3000 --no-clipboard", 3000),
        ]

    # 3. Kill stale processes on the target port
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{sandbox_url}/tasks",
                json={
                    "command": f"pkill -f 'port {port}' || true",
                    "args": [],
                    "workDir": work_dir,
                },
            )
            await asyncio.sleep(1)
    except Exception:
        pass

    # 4. Try each strategy, poll for health
    for cmd, cmd_port in strategies:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{sandbox_url}/tasks",
                    json={"command": cmd, "args": [], "workDir": work_dir},
                )
                resp.raise_for_status()
        except Exception as e:
            logger.warning(
                "Failed to start dev server for task %s: %s", task_id, e
            )
            continue

        # Poll until healthy (30s)
        for _ in range(15):
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    health = await client.get(
                        f"{sandbox_url}/proxy/{cmd_port}/"
                    )
                    if health.status_code < 500:
                        preview = {
                            "url": f"/api/dev/{task_id}/preview/",
                            "taskId": task_id,
                            "port": cmd_port,
                        }
                        _live_previews[task_id] = preview
                        logger.info(
                            "Restarted dev server for task %s (mode=%s, "
                            "dir=%s) on port %d",
                            task_id, mode, work_dir, cmd_port,
                        )
                        return preview
            except Exception:
                pass

    raise HTTPException(
        status_code=504,
        detail=(
            "Dev server failed to start within timeout. "
            "The workspace exists but the server could not be launched."
        ),
    )


def set_dev_service(service: InMemoryDevService, pipeline_fn=None, skills_service=None, cosmos_skills=None, spec_service=None, dev_agent=None) -> None:
    global _dev_service, _pipeline_fn, _skills_service, _cosmos_skills, _spec_service, _dev_agent
    _dev_service = service
    _pipeline_fn = pipeline_fn
    _skills_service = skills_service
    _cosmos_skills = cosmos_skills
    _spec_service = spec_service
    _dev_agent = dev_agent


def _get_service() -> InMemoryDevService:
    if _dev_service is None:
        raise HTTPException(status_code=503, detail="Dev service unavailable")
    return _dev_service


@router.get("", response_model=list[DevTask])
async def list_dev_tasks(request: Request, archived: bool | None = None):
    user_id = getattr(request.state, "user_id", "default-user")
    tasks = await _get_service().with_user(user_id).list()
    if archived is not None:
        tasks = [t for t in tasks if getattr(t, "archived", False) == archived]
    return tasks


@router.get("/suggest-skills")
async def suggest_skills(request: Request, specId: str = ""):
    """Suggest skills for a spec based on keyword matching against activated skills."""
    from app.services.skills_service import SkillsService
    svc = _skills_service or SkillsService()
    if not specId:
        return {"skillIds": []}
    user_id = getattr(request.state, "user_id", "default-user")
    from app.routes import specs as specs_mod
    spec_svc = specs_mod._spec_service
    if not spec_svc:
        return {"skillIds": []}
    spec = await spec_svc.with_user(user_id).get_by_id(specId)
    if not spec:
        return {"skillIds": []}
    content = f"{spec.title} {spec.content}"
    # Get activated skills for matching
    activated = []
    if _cosmos_skills:
        activated = await _cosmos_skills.with_user(user_id).list_activated()
    suggested = svc.suggest_skills_for_content(content, activated)
    return {"skillIds": suggested}


@router.post("/skills/upload-local")
async def upload_local_skills(
    request: Request,
    skill_name: str,
    files: list[UploadFile],
):
    """Upload local skill files for sandbox use.

    In Azure: uploads to Blob Storage (sandbox syncs from there).
    Locally: writes to LOCAL_SKILLS_DIR (volume-mounted into sandbox).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if not skill_name:
        raise HTTPException(status_code=400, detail="skill_name is required")

    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")

    # ── Local fallback: write directly to LOCAL_SKILLS_DIR ────────────
    if not storage_account:
        from app.services.in_memory_skills_service import InMemorySkillsService

        svc = _cosmos_skills
        if svc is None:
            logger.warning(
                "upload_skill: _cosmos_skills is None — service not initialized yet"
            )
        if isinstance(svc, InMemorySkillsService) and svc._local_skills_dir:
            file_pairs: list[tuple[str, bytes]] = []
            for file in files:
                content = await file.read()
                file_pairs.append((file.filename, content))
            written = svc.write_skill_files(skill_name, file_pairs)
            logger.info(
                "upload_skill: wrote %d file(s) for '%s' → %s",
                len(written), skill_name, svc._local_skills_dir / skill_name,
            )

            # Best-effort sandbox sync
            from app.main import _sync_sandbox_skills
            await _sync_sandbox_skills()

            return {
                "success": True,
                "skillName": skill_name,
                "uploadedFiles": written,
                "message": (
                    f"Wrote {len(written)} file(s) for skill '{skill_name}' to local skills dir. "
                    "The sandbox will pick them up via the volume mount."
                ),
            }
        raise HTTPException(
            status_code=503,
            detail="Blob Storage not configured and local skills dir unavailable",
        )

    # ── Azure path: upload to Blob Storage ────────────────────────────
    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient

        credential = DefaultAzureCredential()
        blob_service = BlobServiceClient(
            account_url=f"https://{storage_account}.blob.core.windows.net",
            credential=credential,
        )
        uploaded = []
        async with blob_service:
            container = blob_service.get_container_client("skills")
            try:
                await container.create_container()
            except Exception:
                pass  # Container may already exist
            for file in files:
                blob_path = f"{skill_name}/{file.filename}"
                content = await file.read()
                blob_client = container.get_blob_client(blob_path)
                await blob_client.upload_blob(content, overwrite=True)
                uploaded.append(blob_path)
                logger.info("Uploaded skill file: %s", blob_path)
        await credential.close()

        # Hot-reload: push to running sandbox immediately
        from app.main import _sync_sandbox_skills
        await _sync_sandbox_skills()

        return {
            "success": True,
            "skillName": skill_name,
            "uploadedFiles": uploaded,
            "message": (
                f"Uploaded {len(uploaded)} file(s) for skill '{skill_name}'. "
                "Files will be available in the sandbox on next container restart."
            ),
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Azure SDK not available — install azure-identity and azure-storage-blob",
        )
    except Exception as e:
        logger.exception("Failed to upload skill files to Blob Storage")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/{task_id}", response_model=DevTask)
async def get_dev_task(task_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    task = await _get_service().with_user(user_id).get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    return task


@router.post("", response_model=DevTask)
async def create_dev_task(data: DevTaskCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    task = await svc.create(data)
    # If linked to a spec, populate iterations and set bidirectional link
    if data.spec_id and _spec_service:
        try:
            if _dev_agent:
                await _dev_agent._populate_iterations_from_spec(task.id, data.spec_id, data.mode, user_id=user_id)
            await _spec_service.with_user(user_id).set_dev_task_id(data.spec_id, task.id, "in-development")
        except Exception:
            logger.exception("Failed to populate iterations / link spec for task %s", task.id)
    # Auto-attach skills if none were explicitly provided (skip for slides)
    if not data.skill_ids and _cosmos_skills and data.mode != "slides":
        try:
            content = data.title
            if data.spec_id and _spec_service:
                spec = await _spec_service.with_user(user_id).get_by_id(data.spec_id)
                if spec:
                    content = f"{spec.title} {spec.content} {data.title}"
            activated = await _cosmos_skills.with_user(user_id).list_activated()
            suggested = _skills_service.suggest_skills_for_content(content, activated) if _skills_service else []
            if not suggested:
                suggested = [s["name"] for s in activated]
            if suggested:
                task = await svc.set_skill_ids(task.id, suggested)
                logger.info("Auto-attached skills %s to task %s", suggested, task.id)
        except Exception:
            logger.exception("Failed to auto-attach skills for task %s", task.id)
    # Re-read task to include iterations populated above
    task = await svc.get_by_id(task.id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_dev_task(task_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    logger.info("Deleting dev task %s (user=%s)", task_id, user_id)
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    # Cancel running pipeline asyncio task
    pipeline_task = _running_pipelines.pop(task_id, None)
    if pipeline_task and not pipeline_task.done():
        pipeline_task.cancel()
        logger.info("Cancelled pipeline asyncio task for %s", task_id)
    # Kill any active sandbox task
    killed = await cancel_sandbox_task_for(task_id, dev_agent=_dev_agent)
    if killed:
        logger.info("Killed sandbox task for dev-task %s", task_id)
    # Clear bidirectional link on the spec (and any child feature specs)
    if task.spec_id and _spec_service:
        try:
            spec_svc = _spec_service.with_user(user_id)
            await spec_svc.set_dev_task_id(task.spec_id, None, "optimized")
            features = await spec_svc.get_features_for_foundation(task.spec_id)
            for feature in features:
                if feature.dev_task_id == task_id:
                    await spec_svc.set_dev_task_id(feature.id, None, "optimized")
        except Exception:
            logger.exception("Failed to clear spec links for task %s", task_id)
            # Continue with deletion even if spec link cleanup fails
    deleted = await service.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dev task not found")
    logger.info("Dev task %s deleted successfully", task_id)


@router.patch("/{task_id}/archive", response_model=DevTask)
async def archive_dev_task(task_id: str, request: Request):
    """Archive a dev task."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    return await service.set_archived(task_id, True)


@router.patch("/{task_id}/unarchive", response_model=DevTask)
async def unarchive_dev_task(task_id: str, request: Request):
    """Unarchive a dev task."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    return await service.set_archived(task_id, False)


class TriggerRequest(BaseModel):
    mode: str | None = None  # override mode at trigger time


@router.post("/{task_id}/trigger", response_model=DevTask)
async def trigger_pipeline(task_id: str, request: Request, body: TriggerRequest | None = None):
    """Trigger the dev pipeline (runs in background).

    Returns 503 if the sandbox container is not reachable — the task is set to
    'paused' and the frontend should notify the user.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="Task already completed")
    # If task is "running" but no active pipeline asyncio task exists,
    # it's an orphan from a server restart — allow re-trigger
    if task.status == "running" and task_id in _running_pipelines:
        atask = _running_pipelines[task_id]
        if not atask.done():
            raise HTTPException(status_code=400, detail="Task is already running")
        # Pipeline task finished but status wasn't updated — clean up
        _running_pipelines.pop(task_id, None)
        logger.warning("Orphaned pipeline task %s found done, allowing re-trigger", task_id)

    # Check sandbox availability before starting the pipeline
    from app.routes.sandbox import _probe_sandbox_health

    reachable, _, _ = await _probe_sandbox_health()
    if not reachable:
        await service.set_status(task_id, "paused")
        logger.warning("Sandbox unreachable — task %s paused", task_id)
        raise HTTPException(
            status_code=503,
            detail="Sandbox is not running. Task is paused until the sandbox is available.",
        )

    # Reset stage timestamps before re-running
    raw_doc = await service.get_raw(task_id)
    if raw_doc:
        for it in raw_doc.get("iterations", []):
            for stage in it.get("stages", []):
                stage["status"] = "pending"
                stage["startedAt"] = None
                stage["completedAt"] = None
                stage["output"] = None
                stage["error"] = None
        for stage in raw_doc.get("stages", []):
            stage["status"] = "pending"
            stage["startedAt"] = None
            stage["completedAt"] = None
            stage["output"] = None
            stage["error"] = None
        raw_doc["decisions"] = []
        await service.save_raw(raw_doc)

    await service.set_status(task_id, "running")
    logger.info("Triggering pipeline for task %s (mode=%s, user=%s)", task_id, task.mode, user_id)

    if _pipeline_fn:
        async def _safe_pipeline(tid: str, uid: str):
            """Wrapper to ensure pipeline errors are caught and status is finalized."""
            try:
                logger.info("Pipeline background task starting for %s", tid)
                await _pipeline_fn(tid, user_id=uid)
                logger.info("Pipeline background task completed for %s", tid)
                # Ensure status is finalized — pipeline may have already set it
                svc = _get_service().with_user(uid)
                final_task = await svc.get_by_id(tid)
                if final_task and final_task.status == "running":
                    logger.warning("Pipeline returned but task %s still 'running', setting to 'completed'", tid)
                    await svc.set_status(tid, "completed")
            except Exception:
                logger.exception("Pipeline background task FAILED for %s", tid)
                try:
                    await _get_service().with_user(uid).set_status(tid, "failed")
                except Exception:
                    logger.exception("Failed to set error status on task %s", tid)

        try:
            loop = asyncio.get_running_loop()
            atask = loop.create_task(_safe_pipeline(task_id, user_id))
            _running_pipelines[task_id] = atask
            atask.add_done_callback(lambda _: _running_pipelines.pop(task_id, None))
            logger.info("Pipeline task scheduled on event loop for %s", task_id)
        except RuntimeError:
            logger.exception("No running event loop — cannot schedule pipeline for %s", task_id)
            await service.set_status(task_id, "failed")
            raise HTTPException(status_code=500, detail="Failed to start pipeline — no event loop")
    else:
        logger.warning("No pipeline function configured — marking task completed")
        await service.set_status(task_id, "completed")

    return await service.get_by_id(task_id)


class PromptRequest(BaseModel):
    prompt: str


@router.post("/{task_id}/prompt")
async def send_prompt(task_id: str, body: PromptRequest, request: Request):
    """Send a --continue copilot prompt to update an existing dev-task.

    The prompt is executed in the sandbox workspace with full context
    of the previous Copilot session. Output streams into the terminal.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only allow prompts for completed or failed tasks (not while running)
    if task.status == "running" and task_id in _running_pipelines:
        atask = _running_pipelines[task_id]
        if not atask.done():
            raise HTTPException(status_code=400, detail="Task is currently running")

    # Get the DevAgent instance and run send_prompt in background
    if not _dev_agent:
        raise HTTPException(status_code=500, detail="Dev agent not available")

    async def _run_prompt():
        try:
            await _dev_agent.send_prompt(task_id, body.prompt, user_id=user_id)
        except Exception as exc:
            logger.error("Prompt execution failed for %s: %s", task_id, exc)

    loop = asyncio.get_running_loop()
    prompt_task = loop.create_task(_run_prompt())
    _running_pipelines[task_id] = prompt_task

    return {"status": "started", "taskId": task_id}


@router.get("/{task_id}/download")
async def download_archive(task_id: str, request: Request):
    """Download the generated code archive from the sandbox workspace."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    task = await svc.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Each task has its own workspace directory
    work_dir = f"/workspace/{task_id}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{_resolve_sandbox_url(task_id)}/workspace/archive",
                params={"dir": work_dir},
            )
            resp.raise_for_status()

            async def stream_content():
                yield resp.content

            filename = f"{task.title.replace(' ', '-').lower()[:40]}.tar.gz"
            return StreamingResponse(
                stream_content(),
                media_type="application/gzip",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
    except httpx.HTTPError as exc:
        logger.error("Failed to download archive from sandbox: %s", exc)
        raise HTTPException(
            status_code=503, detail="Sandbox is not available for download"
        )


@router.get("/{task_id}/stream")
async def stream_pipeline_output(task_id: str, request: Request):
    """Stream real-time pipeline output as Server-Sent Events.

    Reads from the pipeline output buffer populated by the dev agent
    during sandbox execution. Supports reconnection via Last-Event-ID header
    or ?cursor= query param so clients resume without duplicate data.
    """
    from app.agents.dev_agent import get_pipeline_output

    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    task = await svc.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Resume cursor: Last-Event-ID header (SSE standard) or ?cursor= query param
    resume_cursor = 0
    last_event_id = request.headers.get("Last-Event-ID")
    cursor_param = request.query_params.get("cursor")
    if last_event_id:
        try:
            resume_cursor = int(last_event_id)
        except ValueError:
            pass
    elif cursor_param:
        try:
            resume_cursor = int(cursor_param)
        except ValueError:
            pass

    logger.debug(
        "[SSE-DIAG] Stream opened task=%s user=%s status=%s resume_cursor=%d",
        task_id, user_id, task.status, resume_cursor,
    )

    async def event_stream():
        cursor = resume_cursor
        idle_count = 0
        keepalive_counter = 0
        first_data_sent = False
        while True:
            buf = get_pipeline_output(task_id)
            if cursor < len(buf):
                if not first_data_sent:
                    logger.debug(
                        "[SSE-DIAG] First data for task=%s buf_size=%d cursor=%d",
                        task_id, len(buf), cursor,
                    )
                    first_data_sent = True
                while cursor < len(buf):
                    entry = buf[cursor]
                    cursor += 1
                    # Include event ID so client can resume on reconnect
                    yield f"id: {cursor}\ndata: {__import__('json').dumps(entry)}\n\n"
                    if entry.get("type") == "exit":
                        logger.debug("[SSE-DIAG] Exit event, closing task=%s", task_id)
                        return
                idle_count = 0
                keepalive_counter = 0
            else:
                idle_count += 1
                keepalive_counter += 1
                # Log buffer state periodically (every ~30s)
                if idle_count % 60 == 0:
                    logger.debug(
                        "[SSE-DIAG] Idle task=%s idle_count=%d buf_size=%d cursor=%d",
                        task_id, idle_count, len(buf), cursor,
                    )
                # Send SSE keepalive every ~15s to prevent Azure proxy idle timeout
                if keepalive_counter >= 30:
                    yield ": keepalive\n\n"
                    keepalive_counter = 0
                # Check task status — do this regardless of buffer state.
                # Previously only checked when buf was empty, which caused streams
                # to hang forever when the buffer had unread data but no exit event.
                if idle_count > 10:
                    t = await svc.get_by_id(task_id)
                    if not t or t.status not in ("running", "pending"):
                        logger.debug(
                            "[SSE-DIAG] Task done/gone, injecting exit task=%s status=%s buf=%d cursor=%d",
                            task_id, t.status if t else "None", len(buf), cursor,
                        )
                        # Flush remaining buffer entries before closing
                        while cursor < len(buf):
                            entry = buf[cursor]
                            cursor += 1
                            yield f"id: {cursor}\ndata: {__import__('json').dumps(entry)}\n\n"
                            if entry.get("type") == "exit":
                                return
                        # Inject synthetic exit if pipeline never emitted one
                        code = 1 if (t and t.status == "failed") else 0
                        yield f"data: {__import__('json').dumps({'type': 'exit', 'code': code})}\n\n"
                        return
                # Stop after 10 min of no new output
                if idle_count > 1200:
                    logger.debug("[SSE-DIAG] 10min idle timeout task=%s", task_id)
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{task_id}/stream-debug")
async def stream_debug(task_id: str, request: Request):
    """Diagnostic endpoint: return pipeline buffer state without SSE."""
    from app.agents.dev_agent import get_pipeline_output

    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    task = await svc.get_by_id(task_id)
    buf = get_pipeline_output(task_id)
    return {
        "task_id": task_id,
        "task_exists": task is not None,
        "task_status": task.status if task else None,
        "buffer_size": len(buf),
        "buffer_has_data": len(buf) > 0,
        "last_5_types": [e.get("type") for e in buf[-5:]] if buf else [],
        "pipeline_output_keys": list(
            __import__("app.agents.dev_agent", fromlist=["_pipeline_outputs"])
            ._pipeline_outputs.keys()
        ),
    }


# ── Live preview endpoints ───────────────────────────────────────────────────


@router.post("/{task_id}/live")
async def start_live_preview(task_id: str, request: Request):
    """Start or re-start the live preview dev server for a completed task.

    If the dev server is already running (registered in _live_previews), returns
    the existing preview URL. Otherwise, verifies the pipeline stage completed
    and restarts the dev server from the persisted workspace files.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service()
    task = await service.with_user(user_id).get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Determine which stage must complete before preview is available
    if task.mode == "slides":
        preview_stages = ["run", "slides"]
    elif task.mode == "mockup":
        preview_stages = ["implement"]
    elif task.mode == "sequential":
        preview_stages = ["implement-foundation"]
    else:
        raise HTTPException(
            status_code=400, detail=f"Live preview not supported for mode '{task.mode}'"
        )

    # Already registered — verify the server is actually reachable
    if task_id in _live_previews:
        preview = _live_previews[task_id]
        port = preview.get("port", 3333)
        try:
            sandbox_url = _resolve_sandbox_url(task_id)
            async with httpx.AsyncClient(timeout=5) as client:
                probe = await client.get(f"{sandbox_url}/proxy/{port}/")
                if probe.status_code < 500:
                    return preview
        except Exception:
            pass
        # Server was registered but is not responding — remove stale entry and restart
        _live_previews.pop(task_id, None)
        logger.info("Stale preview entry for task %s — will restart dev server", task_id)

    # Check if any of the required stages completed
    stage_completed = False
    if task.iterations:
        for stage in task.iterations[0].stages:
            if stage.name in preview_stages and stage.status == "completed":
                stage_completed = True
                break

    if not stage_completed:
        raise HTTPException(
            status_code=409,
            detail=f"None of {preview_stages} stages have completed yet — dev server not started",
        )

    # Stage completed — restart the dev server from persisted workspace files
    return await _restart_dev_server(task_id, task.mode)


@router.get("/{task_id}/live")
async def get_live_preview(task_id: str):
    """Check if a live preview is running for this task."""
    if task_id not in _live_previews:
        return {"running": False}
    return {**_live_previews[task_id], "running": True}


@router.delete("/{task_id}/live")
async def stop_live_preview(task_id: str):
    """Stop a running live preview."""
    preview = _live_previews.pop(task_id, None)
    if not preview:
        raise HTTPException(status_code=404, detail="No live preview running")
    sandbox_task_id = preview.get("sandboxTaskId")
    if sandbox_task_id:
        try:
            async with httpx.AsyncClient(base_url=_resolve_sandbox_url(task_id), timeout=10) as client:
                await client.delete(f"/tasks/{sandbox_task_id}")
        except Exception:
            pass
    return {"stopped": True}


@router.get("/{task_id}/preview/{path:path}")
async def proxy_live_preview(task_id: str, path: str, request: Request):
    """Reverse proxy: voice.turboagent.nl → backend → sandbox → localhost:3333."""
    if task_id not in _live_previews:
        # Auto-recover: if pipeline stage completed, restart the dev server
        user_id = getattr(request.state, "user_id", "default-user")
        task = await _get_service().with_user(user_id).get_by_id(task_id)
        if task and task.iterations:
            preview_stages = (
                ["run", "slides"] if task.mode == "slides"
                else ["implement"] if task.mode == "mockup"
                else ["implement-foundation"] if task.mode == "sequential"
                else []
            )
            stage_ok = preview_stages and any(
                s.name in preview_stages and s.status == "completed"
                for s in task.iterations[0].stages
            )
            if stage_ok:
                try:
                    await _restart_dev_server(task_id, task.mode)
                except HTTPException:
                    pass  # Fall through to the 404 below
        if task_id not in _live_previews:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No live preview available for this task. "
                    "The pipeline run stage must complete before the preview is accessible."
                ),
            )

    port = _live_previews[task_id].get("port", 3333)
    target_url = f"{_resolve_sandbox_url(task_id).rstrip('/')}/proxy/{port}/{path}"
    query = str(request.url.query)
    if query:
        target_url += f"?{query}"

    body = await request.body() if request.method in ("POST", "PUT", "PATCH") else None
    fwd_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "authorization")
    }

    # Retry a few times — dev server may still be starting
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=fwd_headers,
                    content=body,
                )
                excluded = {"transfer-encoding", "connection", "keep-alive"}
                headers = {
                    k: v for k, v in resp.headers.items()
                    if k.lower() not in excluded
                }

                content = resp.content
                ct = resp.headers.get("content-type", "")

                # Rewrite absolute paths in HTML/JS so they route through
                # the proxy instead of hitting the backend root directly.
                # Vite emits src="/@vite/client", from "/@react-refresh", etc.
                if "text/html" in ct or "javascript" in ct:
                    proxy_base = f"/api/dev/{task_id}/preview"
                    text = content.decode("utf-8", errors="replace")
                    # src="/..." and href="/..."
                    text = re.sub(
                        r'((?:src|href)\s*=\s*")/',
                        rf"\1{proxy_base}/",
                        text,
                    )
                    # ES module imports: from "/...", import("/..."),
                    # and side-effect imports: import "/..."
                    text = re.sub(
                        r'''(from\s+['"])\/''',
                        rf"\1{proxy_base}/",
                        text,
                    )
                    text = re.sub(
                        r'''(import\(\s*['"])\/''',
                        rf"\1{proxy_base}/",
                        text,
                    )
                    text = re.sub(
                        r'''(import\s+['"])\/''',
                        rf"\1{proxy_base}/",
                        text,
                    )
                    content = text.encode("utf-8")
                    headers.pop("content-length", None)

                return Response(
                    content=content,
                    status_code=resp.status_code,
                    headers=headers,
                )
        except httpx.ConnectError:
            if attempt < 2:
                await asyncio.sleep(2)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {e}")

    raise HTTPException(
        status_code=502,
        detail="Dev server not reachable — it may still be starting up. Try again in a few seconds.",
    )
