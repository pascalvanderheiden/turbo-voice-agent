"""Brainstorm REST API routes."""

from fastapi import APIRouter, HTTPException, Request

from app.models.idea import Idea, IdeaCreate, IdeaUpdate

router = APIRouter(prefix="/api/ideas", tags=["ideas"])

# Injected at startup
_brainstorm_service = None
_refine_fn = None


def set_brainstorm_service(service, refine_fn=None) -> None:
    global _brainstorm_service, _refine_fn
    _brainstorm_service = service
    _refine_fn = refine_fn


def _get_service():
    if _brainstorm_service is None:
        raise HTTPException(status_code=503, detail="Brainstorm service unavailable")
    return _brainstorm_service


@router.get("", response_model=list[Idea])
async def list_ideas(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/{idea_id}", response_model=Idea)
async def get_idea(idea_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    idea = await _get_service().with_user(user_id).get_by_id(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.post("", response_model=Idea, status_code=201)
async def create_idea(data: IdeaCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    idea = await _get_service().with_user(user_id).create(data)
    if idea is None:
        raise HTTPException(status_code=500, detail="Failed to create idea")
    return idea


@router.put("/{idea_id}", response_model=Idea)
async def update_idea(idea_id: str, data: IdeaUpdate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    idea = await _get_service().with_user(user_id).update(idea_id, data)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.delete("/{idea_id}", status_code=204)
async def delete_idea(idea_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    deleted = await _get_service().with_user(user_id).delete(idea_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Idea not found")


@router.post("/{idea_id}/refine", response_model=Idea)
async def refine_idea(idea_id: str, request: Request):
    """Refine an idea using GPT-5.2."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    idea = await service.get_by_id(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    if _refine_fn is None:
        raise HTTPException(status_code=503, detail="Refine not available")

    draft = await _refine_fn(idea)
    result = await service.set_refined(idea_id, draft)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to store refined draft")
    return result


# Research linked to idea — injected from main.py
_research_service = None


def set_idea_research_service(research_service) -> None:
    global _research_service
    _research_service = research_service


@router.get("/{idea_id}/research")
async def list_idea_research(idea_id: str, request: Request):
    """List research entries linked to an idea."""
    if _research_service is None:
        return []
    user_id = getattr(request.state, "user_id", "default-user")
    return await _research_service.with_user(user_id).list_by_idea(idea_id)
