"""User profile routes."""
from __future__ import annotations

import logging
import os
import uuid

import aiohttp
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["user"])

ALLOWED_PHOTO_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB


def _get_user(request: Request) -> tuple[str, dict]:
    """Extract user_id and claims from request state."""
    user_id = getattr(request.state, "user_id", None)
    claims = getattr(request.state, "user_claims", {})
    return user_id, claims


@router.get("/me")
async def get_profile(request: Request):
    """Get the authenticated user's profile."""
    user_id, claims = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    svc = request.app.state.user_profile_service
    if svc is None:
        # Return basic profile from token claims if no Cosmos
        return {
            "id": user_id,
            "userId": user_id,
            "displayName": claims.get("name", ""),
            "email": claims.get("preferred_username", ""),
            "locale": "en",
            "avatarUrl": None,
            "profilePhotoUrl": None,
        }

    profile = await svc.get_profile(user_id)
    if profile is None:
        # Auto-create on first access
        profile = await svc.upsert_on_login(
            user_id,
            claims.get("name", ""),
            claims.get("preferred_username", ""),
        )
    return profile


@router.patch("/me")
async def update_profile(request: Request):
    """Update profile fields (currently only locale)."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    body = await request.json()
    locale = body.get("locale")
    if not locale:
        return JSONResponse(status_code=400, content={"detail": "locale is required"})

    svc = request.app.state.user_profile_service
    if svc is None:
        return {"locale": locale}

    profile = await svc.update_locale(user_id, locale)
    if profile is None:
        return JSONResponse(status_code=404, content={"detail": "Profile not found"})
    return profile


@router.get("/me/photo")
async def get_profile_photo(request: Request):
    """Get profile photo — check Blob Storage first, then proxy Microsoft Graph."""
    user_id, _ = _get_user(request)

    # Check if user has a custom uploaded photo in Blob Storage
    if user_id:
        svc = request.app.state.user_profile_service
        if svc:
            profile = await svc.get_profile(user_id)
            if profile and profile.get("profilePhotoUrl"):
                photo_url = profile["profilePhotoUrl"]
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            photo_url,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status == 200:
                                photo_data = await resp.read()
                                content_type = resp.headers.get("Content-Type", "image/jpeg")
                                return Response(content=photo_data, media_type=content_type)
                except Exception:
                    logger.warning("Failed to fetch custom profile photo for user %s", user_id)

    # Fallback to Microsoft Graph photo
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "No token"})

    token = auth_header[7:]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://graph.microsoft.com/v1.0/me/photo/$value",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    photo_data = await resp.read()
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    return Response(content=photo_data, media_type=content_type)
                else:
                    return JSONResponse(status_code=404, content={"detail": "No photo available"})
    except Exception:
        return JSONResponse(status_code=404, content={"detail": "No photo available"})


@router.post("/me/photo")
async def upload_profile_photo(request: Request, file: UploadFile = File(...)):
    """Upload a custom profile photo to Blob Storage."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    # Validate file type
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid file type. Allowed: {', '.join(ALLOWED_PHOTO_TYPES)}"},
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_PHOTO_SIZE:
        return JSONResponse(
            status_code=400,
            content={"detail": f"File too large. Maximum size: {MAX_PHOTO_SIZE // (1024*1024)}MB"},
        )

    # Try to upload to Blob Storage
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if storage_account:
        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.storage.blob.aio import BlobServiceClient

            ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
            blob_name = f"profile-photos/{user_id}/{uuid.uuid4()}.{ext}"

            credential = DefaultAzureCredential()
            blob_service = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential,
            )
            async with blob_service:
                container_client = blob_service.get_container_client("uploads")
                # Ensure container exists
                try:
                    await container_client.create_container()
                except Exception:
                    pass  # Container may already exist
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(content, content_type=file.content_type, overwrite=True)
                photo_url = f"https://{storage_account}.blob.core.windows.net/uploads/{blob_name}"

            await credential.close()

            # Update profile with photo URL
            svc = request.app.state.user_profile_service
            if svc:
                await svc.update_profile_photo_url(user_id, photo_url)

            logger.info("Uploaded profile photo for user %s: %s", user_id, blob_name)
            return {"success": True, "photoUrl": photo_url}

        except Exception:
            logger.exception("Failed to upload profile photo to Blob Storage")
            return JSONResponse(status_code=500, content={"detail": "Failed to upload photo"})
    else:
        # Local dev: save to uploads directory
        from pathlib import Path
        upload_dir = Path(__file__).parent.parent.parent / "uploads" / "profile-photos"
        upload_dir.mkdir(parents=True, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"{user_id}_{uuid.uuid4()}.{ext}"
        filepath = upload_dir / filename
        filepath.write_bytes(content)
        photo_url = f"/uploads/profile-photos/{filename}"

        svc = request.app.state.user_profile_service
        if svc:
            await svc.update_profile_photo_url(user_id, photo_url)

        logger.info("Saved profile photo locally for user %s: %s", user_id, filename)
        return {"success": True, "photoUrl": photo_url}
