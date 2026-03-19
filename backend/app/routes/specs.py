"""Spec REST API routes.

Route ordering: ALL named (static) routes are defined BEFORE any
parameterised ``{spec_id}`` routes so that FastAPI/Starlette never
accidentally matches a literal path segment like ``import-openspec`` or
``generate`` as a ``spec_id`` value.

Revision: 2026-03-19 – import-openspec + blob storage + UUID guard
"""

import logging
import os
import re
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.models.spec import Spec, SpecCreate, SpecUpdate
from app.utils.openspec_parser import parse_openspec_folder, synthesize_change_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/specs", tags=["specs"])

_spec_service = None
_optimize_fn = None
_generate_fn = None
_add_feature_fn = None
_brainstorm_service = None

# UUID-v4 pattern used to guard {spec_id} routes
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def set_spec_service(
    service,
    optimize_fn=None,
    generate_fn=None,
    add_feature_fn=None,
    brainstorm_service=None,
) -> None:
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


def _validate_spec_id(spec_id: str) -> None:
    """Reject non-UUID spec_id early so named routes never shadow."""
    if not _UUID_RE.match(spec_id):
        raise HTTPException(status_code=404, detail="Spec not found")


# ---------------------------------------------------------------------------
# Static / named routes — MUST come first
# ---------------------------------------------------------------------------

@router.get("", response_model=list[Spec])
async def list_specs(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.post("", response_model=Spec, status_code=201)
async def create_spec(data: SpecCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).create(data)
    if spec is None:
        raise HTTPException(status_code=500, detail="Failed to create spec")
    return spec


@router.post("/import-openspec")
async def import_openspec(
    request: Request,
    files: Annotated[list[UploadFile], File()],
    folder_name: Annotated[str, Form()] = "imported-project",
):
    """Import a local OpenSpec project folder into the spec system.

    Creates one foundation spec (from project.md + change history) and
    one feature spec per specs/<name>/spec.md found in the upload.
    All created specs are tagged with formatVersion='imported'.
    Uploaded source files are stored in Azure Blob Storage for reference.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)

    # Reconstruct folder structure from uploaded files
    file_map: dict[str, str] = {}
    for f in files:
        content = (await f.read()).decode("utf-8", errors="replace")
        path = f.filename or f.headers.get("filename", "unknown")
        file_map[path] = content

    if not file_map:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Parse the OpenSpec folder
    try:
        parsed = parse_openspec_folder(file_map, folder_name=folder_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build foundation spec content
    foundation_parts: list[str] = []
    if parsed.project_context:
        foundation_parts.append(f"## Project Context\n\n{parsed.project_context.strip()}")

    change_history = synthesize_change_history(parsed.changes)
    if change_history:
        foundation_parts.append(change_history.strip())

    # Add a summary of included specs
    spec_names = [s.name for s in parsed.specs]
    foundation_parts.append(
        "## Capabilities\n\n"
        + "\n".join(f"- **{name}**" for name in spec_names)
    )

    foundation_content = "\n\n".join(foundation_parts)

    # Create foundation spec
    foundation = await service.create(SpecCreate(
        title=f"{folder_name} (imported)",
        content=foundation_content,
        type="foundation",
        formatVersion="imported",
    ))
    if foundation is None:
        raise HTTPException(status_code=500, detail="Failed to create foundation spec")

    # Create feature specs
    feature_count = 0
    for spec in parsed.specs:
        feature = await service.create(SpecCreate(
            title=spec.name,
            content=spec.content,
            type="feature",
            parentId=foundation.id,
            formatVersion="imported",
        ))
        if feature:
            feature_count += 1

    # Store raw source files in Azure Blob Storage for reference
    blob_prefix = await _upload_to_blob_storage(user_id, foundation.id, file_map)

    logger.info(
        "Imported OpenSpec project '%s': foundation=%s, %d features, %d changes, blob=%s",
        folder_name, foundation.id, feature_count, len(parsed.changes), blob_prefix or "skipped",
    )

    return {
        "foundationId": foundation.id,
        "featureCount": feature_count,
        "changesFound": len(parsed.changes),
    }


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


# ---------------------------------------------------------------------------
# Parameterised {spec_id} routes — MUST come after all named routes
# ---------------------------------------------------------------------------

@router.get("/{spec_id}", response_model=Spec)
async def get_spec(spec_id: str, request: Request):
    _validate_spec_id(spec_id)
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec


@router.put("/{spec_id}", response_model=Spec)
async def update_spec(spec_id: str, data: SpecUpdate, request: Request):
    _validate_spec_id(spec_id)
    user_id = getattr(request.state, "user_id", "default-user")
    spec = await _get_service().with_user(user_id).update(spec_id, data)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec


@router.delete("/{spec_id}", status_code=204)
async def delete_spec(spec_id: str, request: Request):
    _validate_spec_id(spec_id)
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
    _validate_spec_id(spec_id)
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


class AddFeatureRequest(BaseModel):
    description: str = Field(..., min_length=1)


@router.post("/{spec_id}/add-feature")
async def add_feature_to_spec(spec_id: str, data: AddFeatureRequest, request: Request):
    """Add a new feature to a foundation spec, enhanced with AI."""
    _validate_spec_id(spec_id)
    if _add_feature_fn is None:
        raise HTTPException(status_code=503, detail="Add feature not available")

    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    spec = await service.get_by_id(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Spec not found")
    if spec.type != "foundation":
        raise HTTPException(
            status_code=400, detail="Features can only be added to foundation specs"
        )

    try:
        result = await _add_feature_fn(spec_id, data.description, user_id=user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add feature: {str(e)}")


# ---------------------------------------------------------------------------
# Blob Storage helper for imported OpenSpec files
# ---------------------------------------------------------------------------

async def _upload_to_blob_storage(
    user_id: str,
    foundation_id: str,
    file_map: dict[str, str],
) -> str | None:
    """Upload raw imported files to Azure Blob Storage.

    Returns the blob prefix on success, or None if storage is unavailable.
    """
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account:
        logger.debug("Blob storage not configured — skipping openspec upload")
        return None

    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient

        prefix = f"openspec-imports/{user_id}/{foundation_id}"
        credential = DefaultAzureCredential()
        blob_service = BlobServiceClient(
            account_url=f"https://{storage_account}.blob.core.windows.net",
            credential=credential,
        )
        async with blob_service:
            container_client = blob_service.get_container_client("openspec-imports")
            try:
                await container_client.create_container()
            except Exception:
                pass  # Container may already exist

            for path, content in file_map.items():
                blob_name = f"{user_id}/{foundation_id}/{path}"
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(
                    content.encode("utf-8"),
                    content_type="text/markdown",
                    overwrite=True,
                )

        await credential.close()
        logger.info("Uploaded %d files to blob: %s", len(file_map), prefix)
        return prefix
    except Exception:
        logger.exception("Failed to upload openspec files to blob storage")
        return None
