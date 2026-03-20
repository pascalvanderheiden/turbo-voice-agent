"""Slides REST API routes."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.slides import Slides, SlidesCreate, SlidesUpdate

router = APIRouter(prefix="/api/slides", tags=["slides"])

# Injected at startup
_slides_service = None
_refine_fn = None
_refine_stream_fn = None


def set_slides_service(service, refine_fn=None, refine_stream_fn=None) -> None:
    global _slides_service, _refine_fn, _refine_stream_fn
    _slides_service = service
    _refine_fn = refine_fn
    _refine_stream_fn = refine_stream_fn


def _get_service():
    if _slides_service is None:
        raise HTTPException(status_code=503, detail="Slides service unavailable")
    return _slides_service


@router.get("", response_model=list[Slides])
async def list_slides(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/{slides_id}", response_model=Slides)
async def get_slides(slides_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    slides = await _get_service().with_user(user_id).get_by_id(slides_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return slides


@router.post("", response_model=Slides, status_code=201)
async def create_slides(data: SlidesCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    slides = await _get_service().with_user(user_id).create(data)
    if slides is None:
        raise HTTPException(status_code=500, detail="Failed to create presentation")
    return slides


@router.put("/{slides_id}", response_model=Slides)
async def update_slides(slides_id: str, data: SlidesUpdate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    slides = await _get_service().with_user(user_id).update(slides_id, data)
    if slides is None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return slides


@router.delete("/{slides_id}", status_code=204)
async def delete_slides(slides_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    deleted = await _get_service().with_user(user_id).delete(slides_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Presentation not found")


@router.post("/{slides_id}/refine", response_model=Slides)
async def refine_slides(slides_id: str, request: Request):
    """Refine a presentation using GPT-5.2."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    slides = await service.get_by_id(slides_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="Presentation not found")

    if _refine_fn is None:
        raise HTTPException(status_code=503, detail="Refine not available")

    draft = await _refine_fn(slides)
    result = await service.set_refined(slides_id, draft)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to store refined draft")
    return result


@router.post("/{slides_id}/refine/stream")
async def refine_slides_stream(slides_id: str, request: Request):
    """Stream-refine a presentation — returns SSE text/event-stream with partial tokens."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    slides = await service.get_by_id(slides_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="Presentation not found")

    stream_fn = _refine_stream_fn or _refine_fn
    if stream_fn is None:
        raise HTTPException(status_code=503, detail="Refine not available")

    if _refine_stream_fn is None:
        draft = await _refine_fn(slides)
        await service.set_refined(slides_id, draft)

        async def _single():
            yield f"data: {draft}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_single(), media_type="text/event-stream")

    collected: list[str] = []

    async def _generate():
        async for chunk in _refine_stream_fn(slides):
            collected.append(chunk)
            yield f"data: {chunk}\n\n"
        full = "".join(collected)
        await service.set_refined(slides_id, full)
        yield "data: [DONE]\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


# Research linked to slides — injected from main.py
_research_service = None


def set_slides_research_service(research_service) -> None:
    global _research_service
    _research_service = research_service


@router.get("/{slides_id}/research")
async def list_slides_research(slides_id: str, request: Request):
    """List research entries linked to a presentation."""
    if _research_service is None:
        return []
    user_id = getattr(request.state, "user_id", "default-user")
    return await _research_service.with_user(user_id).list_by_idea(slides_id)
