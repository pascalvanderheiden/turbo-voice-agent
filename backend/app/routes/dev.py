"""Development Task REST API routes."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.dev_task import DevTask, DevTaskCreate
from app.services.dev_service import InMemoryDevService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dev", tags=["development"])

_dev_service: InMemoryDevService | None = None
_pipeline_fn = None
_skills_service = None
_spec_service = None
_dev_agent = None


def set_dev_service(service: InMemoryDevService, pipeline_fn=None, skills_service=None, spec_service=None, dev_agent=None) -> None:
    global _dev_service, _pipeline_fn, _skills_service, _spec_service, _dev_agent
    _dev_service = service
    _pipeline_fn = pipeline_fn
    _skills_service = skills_service
    _spec_service = spec_service
    _dev_agent = dev_agent


def _get_service() -> InMemoryDevService:
    if _dev_service is None:
        raise HTTPException(status_code=503, detail="Dev service unavailable")
    return _dev_service


@router.get("", response_model=list[DevTask])
async def list_dev_tasks(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/suggest-skills")
async def suggest_skills(request: Request, specId: str = ""):
    """Suggest skills for a spec based on keyword matching."""
    from app.services.skills_service import SkillsService
    svc = _skills_service or SkillsService()
    if not specId:
        return {"skillIds": []}
    # Access spec service from specs routes module
    user_id = getattr(request.state, "user_id", "default-user")
    from app.routes import specs as specs_mod
    spec_svc = specs_mod._spec_service
    if not spec_svc:
        return {"skillIds": []}
    spec = await spec_svc.with_user(user_id).get_by_id(specId)
    if not spec:
        return {"skillIds": []}
    content = f"{spec.title} {spec.content}"
    suggested = svc.suggest_skills_for_content(content)
    return {"skillIds": suggested}


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
    if data.spec_id and _spec_service and _dev_agent:
        await _dev_agent._populate_iterations_from_spec(task.id, data.spec_id, data.mode, user_id=user_id)
        await _spec_service.with_user(user_id).set_dev_task_id(data.spec_id, task.id, "in-development")
    elif data.spec_id and _spec_service:
        await _spec_service.with_user(user_id).set_dev_task_id(data.spec_id, task.id, "in-development")
    # Auto-attach skills if none were explicitly provided
    if not data.skill_ids and _skills_service:
        content = data.title
        if data.spec_id and _spec_service:
            spec = await _spec_service.with_user(user_id).get_by_id(data.spec_id)
            if spec:
                content = f"{spec.title} {spec.content} {data.title}"
        suggested = _skills_service.suggest_skills_for_content(content)
        # Fallback: include all installed skills if no keyword match
        if not suggested:
            all_skills = _skills_service.list_installed()
            suggested = [s["name"] for s in all_skills[:3]]
        if suggested:
            task = await svc.set_skill_ids(task.id, suggested)
            logger.info("Auto-attached skills %s to task %s", suggested, task.id)
    # Re-read task to include iterations populated above
    task = await svc.get_by_id(task.id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_dev_task(task_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    # Clear bidirectional link on the spec (and any child feature specs)
    if task.spec_id and _spec_service:
        spec_svc = _spec_service.with_user(user_id)
        await spec_svc.set_dev_task_id(task.spec_id, None, "optimized")
        features = await spec_svc.get_features_for_foundation(task.spec_id)
        for feature in features:
            if feature.dev_task_id == task_id:
                await spec_svc.set_dev_task_id(feature.id, None, "optimized")
    deleted = await service.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dev task not found")


class TriggerRequest(BaseModel):
    mode: str | None = None  # override mode at trigger time


@router.post("/{task_id}/trigger", response_model=DevTask)
async def trigger_pipeline(task_id: str, request: Request, body: TriggerRequest | None = None):
    """Trigger the dev pipeline (runs in background)."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    task = await service.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Dev task not found")
    if task.status not in ("pending", "failed"):
        raise HTTPException(status_code=400, detail="Task already running or completed")

    await service.set_status(task_id, "running")

    if _pipeline_fn:
        asyncio.create_task(_pipeline_fn(task_id, user_id=user_id))
    else:
        logger.warning("No pipeline function configured — marking task completed")
        await service.set_status(task_id, "completed")

    return await service.get_by_id(task_id)


@router.get("/{task_id}/download")
async def download_archive(task_id: str, request: Request):
    """Download the generated code archive."""
    from app.services.json_persistence import DATA_DIR
    archive_path = DATA_DIR / "dev" / f"{task_id}.tar.gz"
    if not archive_path.exists():
        raise HTTPException(status_code=404, detail="Archive not found")
    return FileResponse(archive_path, media_type="application/gzip", filename=f"{task_id}.tar.gz")
