"""Research REST API routes."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.research import Research, ResearchCreate
from app.services.memory_research_service import InMemoryResearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_research_service: InMemoryResearchService | None = None
_web_search_fn = None
_deep_research_fn = None


def set_research_service(service, web_search_fn=None, deep_research_fn=None) -> None:
    global _research_service, _web_search_fn, _deep_research_fn
    _research_service = service
    _web_search_fn = web_search_fn
    _deep_research_fn = deep_research_fn


def _get_service():
    if _research_service is None:
        raise HTTPException(status_code=503, detail="Research service unavailable")
    return _research_service


async def _run_search_background(entry_id: str, query: str, search_fn, service):
    """Run a search in the background and update the entry when done."""
    try:
        result_text, citations = await search_fn(query)
        await service.set_result(entry_id, result_text, citations)
        logger.info("Background research %s completed", entry_id)
    except Exception as e:
        logger.exception("Background research %s failed", entry_id)
        await service.set_failed(entry_id, str(e))


@router.get("", response_model=list[Research])
async def list_research(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/{research_id}", response_model=Research)
async def get_research(research_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    entry = await _get_service().with_user(user_id).get_by_id(research_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Research not found")
    return entry


@router.delete("/{research_id}", status_code=204)
async def delete_research(research_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    deleted = await _get_service().with_user(user_id).delete(research_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Research not found")


@router.post("/search", response_model=Research)
async def trigger_web_search(data: ResearchCreate, request: Request):
    """Trigger a web search (runs in background, returns immediately)."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    if _web_search_fn is None:
        raise HTTPException(status_code=503, detail="Web search not available")

    entry = await service.create(
        ResearchCreate(query=data.query, mode="web_search", ideaId=data.idea_id)
    )
    asyncio.create_task(_run_search_background(entry.id, data.query, _web_search_fn, service))
    return entry


@router.post("/deep", response_model=Research)
async def trigger_deep_research(data: ResearchCreate, request: Request):
    """Trigger deep research (runs in background, returns immediately)."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    if _deep_research_fn is None:
        raise HTTPException(status_code=503, detail="Deep research not available")

    entry = await service.create(
        ResearchCreate(query=data.query, mode="deep_research", ideaId=data.idea_id)
    )
    asyncio.create_task(_run_search_background(entry.id, data.query, _deep_research_fn, service))
    return entry
