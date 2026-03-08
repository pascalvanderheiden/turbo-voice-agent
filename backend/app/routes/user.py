"""User profile routes."""
from __future__ import annotations

import logging

import aiohttp
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["user"])


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
    """Proxy Microsoft Graph profile photo using user's token."""
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
