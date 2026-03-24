"""Development Task REST API routes."""

import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.models.dev_task import DevTask, DevTaskCreate
from app.agents.dev_agent import cancel_sandbox_task_for
from app.services.dev_service import InMemoryDevService

logger = logging.getLogger(__name__)

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")

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
    """Upload local skill files to Azure Blob Storage for sandbox use.

    Uploads skill files (SKILL.md + any supporting files) to the `skills`
    container in Blob Storage. The sandbox container downloads these on startup
    into ~/.copilot/skills/, making them available to the Copilot CLI.
    """
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account:
        raise HTTPException(
            status_code=503,
            detail="Blob Storage not configured — set AZURE_STORAGE_ACCOUNT_NAME",
        )
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if not skill_name:
        raise HTTPException(status_code=400, detail="skill_name is required")

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
    killed = await cancel_sandbox_task_for(task_id)
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
                f"{SANDBOX_URL}/workspace/archive",
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


@router.get("/{task_id}/pdf")
async def download_pdf(task_id: str, request: Request):
    """Download the exported PDF from blob storage."""
    user_id = getattr(request.state, "user_id", "default-user")
    svc = _get_service().with_user(user_id)
    task = await svc.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    pdf_url = task.export_artifacts.pdf_url if task.export_artifacts else None
    if not pdf_url:
        raise HTTPException(status_code=404, detail="No PDF available for this task")

    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account:
        raise HTTPException(status_code=500, detail="Storage not configured")

    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient

        credential = DefaultAzureCredential()
        blob_service = BlobServiceClient(
            account_url=f"https://{storage_account}.blob.core.windows.net",
            credential=credential,
        )
        blob_name = f"exports/{task_id}/slides.pdf"
        async with blob_service:
            container = blob_service.get_container_client("exports")
            blob_client = container.get_blob_client(blob_name)
            download = await blob_client.download_blob()
            pdf_bytes = await download.readall()

        filename = f"{task.title.replace(' ', '-').lower()[:40]}-slides.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except Exception as exc:
        logger.error("Failed to download PDF: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to retrieve PDF")


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

    logger.info(
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
                    logger.info(
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
                        logger.info("[SSE-DIAG] Exit event, closing task=%s", task_id)
                        return
                idle_count = 0
                keepalive_counter = 0
            else:
                idle_count += 1
                keepalive_counter += 1
                # Log buffer state periodically (every ~30s)
                if idle_count % 60 == 0:
                    logger.info(
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
                        logger.info(
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
                    logger.info("[SSE-DIAG] 10min idle timeout task=%s", task_id)
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
    """Start npm run dev in the sandbox and return a proxy URL."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service()
    task = await service.with_user(user_id).get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.mode != "slides":
        raise HTTPException(status_code=400, detail="Live preview only available for slides tasks")
    if task_id in _live_previews:
        return _live_previews[task_id]

    # Determine workspace path
    deck_name = task.title.lower().replace(" ", "-")[:30]
    work_dir = f"/workspace/{task_id}/{deck_name}"

    try:
        async with httpx.AsyncClient(base_url=SANDBOX_URL, timeout=120) as client:
            # Ensure dependencies are installed first
            install_resp = await client.post(
                "/tasks",
                json={
                    "command": f"cd {work_dir} && npm install --silent 2>&1",
                    "args": [],
                    "workDir": work_dir,
                },
            )
            install_resp.raise_for_status()
            install_id = install_resp.json().get("id", "")

            # Wait for npm install to finish (poll status)
            for _ in range(30):
                await asyncio.sleep(2)
                try:
                    status_resp = await client.get(f"/tasks/{install_id}/status")
                    if status_resp.json().get("status") in ("completed", "exited"):
                        break
                except Exception:
                    pass

            # Start dev server with slidev
            resp = await client.post(
                "/tasks",
                json={
                    "command": (
                        f"cd {work_dir}"
                        " && npx slidev --port 3333 --remote 2>&1"
                    ),
                    "args": [],
                    "workDir": work_dir,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            sandbox_task_id = data.get("id", "")

        # Wait for dev server to become responsive
        ready = False
        for _ in range(10):
            await asyncio.sleep(3)
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    probe = await client.get(f"{SANDBOX_URL}/proxy/3333/")
                    if probe.status_code < 500:
                        ready = True
                        break
            except Exception:
                pass
        if not ready:
            logger.warning("Dev server not responsive after 30s for task %s", task_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to start dev server: {e}")

    # URL goes through our own backend proxy → sandbox proxy → localhost:3333
    live_url = f"/api/dev/{task_id}/preview/"
    preview = {"url": live_url, "sandboxTaskId": sandbox_task_id, "taskId": task_id}
    _live_previews[task_id] = preview
    return preview


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
            async with httpx.AsyncClient(base_url=SANDBOX_URL, timeout=10) as client:
                await client.delete(f"/tasks/{sandbox_task_id}")
        except Exception:
            pass
    return {"stopped": True}


@router.get("/{task_id}/preview/{path:path}")
async def proxy_live_preview(task_id: str, path: str, request: Request):
    """Reverse proxy: voice.turboagent.nl → backend → sandbox → localhost:3333."""
    if task_id not in _live_previews:
        raise HTTPException(status_code=404, detail="No live preview running for this task")

    target_url = f"{SANDBOX_URL.rstrip('/')}/proxy/3333/{path}"
    query = str(request.url.query)
    if query:
        target_url += f"?{query}"

    body = await request.body() if request.method in ("POST", "PUT", "PATCH") else None
    fwd_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "authorization")
    }

    # Retry a few times — dev server may still be starting
    last_err = None
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
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=headers,
                )
        except httpx.ConnectError as e:
            last_err = e
            if attempt < 2:
                await asyncio.sleep(2)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {e}")

    raise HTTPException(
        status_code=502,
        detail="Dev server not reachable — it may still be starting up. Try again in a few seconds.",
    )
