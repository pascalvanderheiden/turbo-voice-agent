"""Spec REST API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.spec import Spec, SpecCreate, SpecUpdate

router = APIRouter(prefix="/api/specs", tags=["specs"])

_spec_service = None
_optimize_fn = None
_generate_fn = None
_add_feature_fn = None
_brainstorm_service = None


def set_spec_service(service, optimize_fn=None, generate_fn=None, add_feature_fn=None, brainstorm_service=None) -> None:
    global _spec_service, _optimize_fn, _generate_fn, _add_feature_fn, _brainstorm_service
    _spec_service = service
    _optimize_fn = optimize_fn
    _generate_fn = generate_fn
    _add_feature_fn = add_feature_fn
    _brainstorm_service = brainstorm_service


def _get_service():
    if _spec_service is None:
        raise HTTPException(status_code=503, detail="Spec service unavailable")
    return _spec_service


@router.get("", response_model=list[Spec])
async def list_specs(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/{spec_id}", response_model=Spec)
async def get_spec(spec_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec


@router.post("", response_model=Spec, status_code=201)
async def create_spec(data: SpecCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).create(data)
    if spec is None:
        raise HTTPException(status_code=500, detail="Failed to create spec")
    return spec


@router.put("/{spec_id}", response_model=Spec)
async def update_spec(spec_id: str, data: SpecUpdate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).update(spec_id, data)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec


@router.delete("/{spec_id}", status_code=204)
async def delete_spec(spec_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    spec = await service.get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    # Cascade: delete child features when deleting a foundation
    if spec.type == "foundation":
        all_specs = await service.list()
        for child in all_specs:
            if child.parent_id == spec_id:
                await service.delete(child.id)
    deleted = await service.delete(spec_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Spec not found")


@router.post("/{spec_id}/optimize", response_model=Spec)
async def optimize_spec(spec_id: str, request: Request):
    """Optimize a spec using GPT-5.2."""
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    spec = await service.get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    if _optimize_fn is None:
        raise HTTPException(status_code=503, detail="Optimization not available")
    content = await _optimize_fn(spec)
    result = await service.set_optimized(spec_id, content)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to store optimized spec")
    return result


class GenerateRequest(BaseModel):
    idea_id: str = Field(..., alias="ideaId")
    model_config = {"populate_by_name": True}


@router.post("/generate")
async def generate_specs(data: GenerateRequest, request: Request):
    """Generate foundation + feature specs from an idea."""
    if _generate_fn is None:
        raise HTTPException(status_code=503, detail="Generation not available")
    if _brainstorm_service is None:
        raise HTTPException(status_code=503, detail="Brainstorm service not available")

    user_id = getattr(request.state, "user_id", "default-user")
    idea = await _brainstorm_service.with_user(user_id).get_by_id(data.idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    try:
        specs = await _generate_fn(idea.title, idea.description, idea.id, user_id=user_id)
        return {"success": True, "specs": specs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


class AddFeatureRequest(BaseModel):
    description: str = Field(..., min_length=1)


@router.post("/{spec_id}/add-feature")
async def add_feature_to_spec(spec_id: str, data: AddFeatureRequest, request: Request):
    """Add a new feature to a foundation spec, enhanced with AI."""
    if _add_feature_fn is None:
        raise HTTPException(status_code=503, detail="Add feature not available")

    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    spec = await service.get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    if spec.type != "foundation":
        raise HTTPException(status_code=400, detail="Features can only be added to foundation specs")

    try:
        result = await _add_feature_fn(spec_id, data.description, user_id=user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add feature: {str(e)}")
