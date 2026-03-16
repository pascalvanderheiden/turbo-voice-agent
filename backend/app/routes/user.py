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

# ── In-memory connection store (local dev fallback) ──
_connection_store: dict[str, dict] = {}


def _get_user(request: Request) -> tuple[str, dict]:
    """Extract user_id and claims from request state."""
    user_id = getattr(request.state, "user_id", None)
    claims = getattr(request.state, "user_claims", {})
    return user_id, claims


# ── Microsoft To-Do Connection ──────────────────────────────────


def _todo_oauth_config() -> dict:
    """Return OAuth config for Microsoft To-Do consent.

    Uses 'common' authority by default so both personal Microsoft accounts and
    organizational accounts can consent.  Override with TODO_OAUTH_TENANT_ID if
    you need to restrict to a specific tenant.

    The redirect_uri MUST point to the frontend domain (the Next.js API route
    proxies the callback to the backend).
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return {
        "client_id": os.environ.get("TODO_OAUTH_CLIENT_ID")
        or os.environ.get("ENTRA_CLIENT_ID", ""),
        "tenant_id": os.environ.get("TODO_OAUTH_TENANT_ID", "common"),
        "redirect_uri": os.environ.get(
            "TODO_OAUTH_REDIRECT_URI",
            f"{frontend_url}/api/auth/callback/microsoft-todo",
        ),
        "scope": "offline_access Tasks.ReadWrite",
    }


@router.get("/me/connections/microsoft-todo")
async def get_todo_connection_status(request: Request):
    """Check whether the user has connected Microsoft To-Do."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    conn = _connection_store.get(f"todo:{user_id}")
    if conn:
        return {"connected": True, "connectedAt": conn.get("connectedAt", "")}

    # Check Cosmos profile for persisted connection
    svc = getattr(request.app.state, "user_profile_service", None)
    if svc:
        profile = await svc.get_profile(user_id)
        if profile and profile.get("todoRefreshToken"):
            _connection_store[f"todo:{user_id}"] = {
                "refreshToken": profile["todoRefreshToken"],
                "connectedAt": profile.get("todoConnectedAt", ""),
            }
            return {"connected": True, "connectedAt": profile.get("todoConnectedAt", "")}

    return {"connected": False}


@router.post("/me/connections/microsoft-todo")
async def initiate_todo_connection(request: Request):
    """Start Microsoft OAuth consent flow for To-Do access.

    When AUTH_DISABLED=true, auto-connects with a mock token so the full
    To-Do flow can be tested locally without real Entra credentials.
    """
    import datetime

    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    # Local dev: auto-connect with mock token (no OAuth needed)
    if os.environ.get("AUTH_DISABLED", "").lower() == "true":
        now = datetime.datetime.now(datetime.UTC).isoformat()
        _connection_store[f"todo:{user_id}"] = {
            "refreshToken": "mock-token-auth-disabled",
            "connectedAt": now,
        }
        logger.info("Auto-connected Microsoft To-Do for user %s (AUTH_DISABLED)", user_id)
        return {"connected": True, "connectedAt": now}

    cfg = _todo_oauth_config()
    if not cfg["client_id"]:
        logger.error("ENTRA_CLIENT_ID env var is not set — cannot start OAuth flow")
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Microsoft To-Do connection is not configured. "
                "Set ENTRA_CLIENT_ID in backend .env."
            },
        )

    from urllib.parse import urlencode

    params = urlencode({
        "client_id": cfg["client_id"],
        "response_type": "code",
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg["scope"],
        "state": user_id,
        "prompt": "consent",
    })
    auth_url = (
        f"https://login.microsoftonline.com/{cfg['tenant_id']}"
        f"/oauth2/v2.0/authorize?{params}"
    )
    return {"authUrl": auth_url}


@router.get("/auth/callback/microsoft-todo")
async def todo_oauth_callback(request: Request, code: str = "", error: str = "", state: str = ""):
    """Handle OAuth callback from Microsoft for To-Do consent."""
    import datetime

    from fastapi.responses import RedirectResponse

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    if error or not code:
        logger.warning("Microsoft To-Do OAuth error: %s", error)
        return RedirectResponse(f"{frontend_url}/settings?todo_connected=error")

    user_id = state
    if not user_id:
        return RedirectResponse(f"{frontend_url}/settings?todo_connected=error")

    cfg = _todo_oauth_config()

    # Exchange authorization code for tokens
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token",
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": os.environ.get("ENTRA_CLIENT_SECRET", ""),
                    "code": code,
                    "redirect_uri": cfg["redirect_uri"],
                    "grant_type": "authorization_code",
                    "scope": cfg["scope"],
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Token exchange failed (%d): %s", resp.status, body)
                    return RedirectResponse(f"{frontend_url}/settings?todo_connected=error")

                tokens = await resp.json()
    except Exception:
        logger.exception("Token exchange request failed")
        return RedirectResponse(f"{frontend_url}/settings?todo_connected=error")

    refresh_token = tokens.get("refresh_token", "")
    if not refresh_token:
        logger.error("No refresh_token in token response")
        return RedirectResponse(f"{frontend_url}/settings?todo_connected=error")

    # Store in-memory
    now = datetime.datetime.now(datetime.UTC).isoformat()
    _connection_store[f"todo:{user_id}"] = {
        "refreshToken": refresh_token,
        "connectedAt": now,
    }

    # Persist to Cosmos DB
    svc = getattr(request.app.state, "user_profile_service", None)
    if svc:
        try:
            await svc.update_todo_connection(user_id, refresh_token, now)
        except Exception:
            logger.exception("Failed to persist To-Do token to Cosmos for user %s", user_id)

    logger.info("Microsoft To-Do connected for user %s", user_id)

    return RedirectResponse(f"{frontend_url}/settings?todo_connected=success")


@router.delete("/me/connections/microsoft-todo")
async def disconnect_todo(request: Request):
    """Disconnect Microsoft To-Do — remove stored tokens."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    _connection_store.pop(f"todo:{user_id}", None)

    svc = getattr(request.app.state, "user_profile_service", None)
    if svc:
        try:
            await svc.update_todo_connection(user_id, None, None)
        except Exception:
            logger.exception("Failed to clear To-Do token in Cosmos for user %s", user_id)

    logger.info("Microsoft To-Do disconnected for user %s", user_id)
    return {"connected": False}


# ── GitHub Copilot Sandbox Connection ─────────────────────────


@router.get("/me/connections/github-sandbox")
async def get_sandbox_connection_status(request: Request):
    """Check whether the user has connected GitHub for the Copilot CLI sandbox."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    conn = _connection_store.get(f"sandbox:{user_id}")
    if conn:
        return {"connected": True, "connectedAt": conn.get("connectedAt", "")}

    # Also check Cosmos profile
    svc = request.app.state.user_profile_service
    if svc:
        profile = await svc.get_profile(user_id)
        if profile and profile.get("githubSandboxToken"):
            # Re-populate in-memory cache so sandbox routes can use it
            _connection_store[f"sandbox:{user_id}"] = {
                "token": profile["githubSandboxToken"],
                "connectedAt": profile.get("githubSandboxConnectedAt", ""),
            }
            return {"connected": True, "connectedAt": profile.get("githubSandboxConnectedAt", "")}

    return {"connected": False}


@router.put("/me/connections/github-sandbox")
async def set_sandbox_token(request: Request):
    """Store a GitHub personal access token for the Copilot CLI sandbox."""
    import datetime

    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    body = await request.json()
    token = body.get("token", "").strip()
    if not token:
        return JSONResponse(status_code=400, content={"detail": "token is required"})

    # Encrypt token before storing
    encrypted = _encrypt_sandbox_token(token)
    now = datetime.datetime.now(datetime.UTC).isoformat()

    # Store in-memory (local dev)
    _connection_store[f"sandbox:{user_id}"] = {
        "token": encrypted,
        "connectedAt": now,
    }

    # Also persist to Cosmos profile if available
    svc = request.app.state.user_profile_service
    if svc:
        try:
            await svc.update_sandbox_token(user_id, encrypted, now)
        except Exception:
            logger.exception("Failed to persist sandbox token to Cosmos for user %s", user_id)

    logger.info("GitHub sandbox token stored for user %s", user_id)
    return {"connected": True, "connectedAt": now}


@router.delete("/me/connections/github-sandbox")
async def disconnect_sandbox(request: Request):
    """Disconnect GitHub sandbox — remove stored token."""
    user_id, _ = _get_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    _connection_store.pop(f"sandbox:{user_id}", None)

    svc = request.app.state.user_profile_service
    if svc:
        try:
            await svc.update_sandbox_token(user_id, None, None)
        except Exception:
            logger.exception("Failed to clear sandbox token in Cosmos for user %s", user_id)

    logger.info("GitHub sandbox disconnected for user %s", user_id)
    return {"connected": False}


def _encrypt_sandbox_token(token: str) -> str:
    """Encrypt a sandbox token using SANDBOX_TOKEN_KEY env var (simple XOR for now)."""
    key = os.environ.get("SANDBOX_TOKEN_KEY", "default-dev-key-not-for-production")
    import base64
    # Simple reversible encoding — production should use Fernet or Azure Key Vault
    key_bytes = key.encode()
    token_bytes = token.encode()
    encrypted = bytes(t ^ key_bytes[i % len(key_bytes)] for i, t in enumerate(token_bytes))
    return base64.b64encode(encrypted).decode()


def _decrypt_sandbox_token(encrypted: str) -> str:
    """Decrypt a sandbox token."""
    key = os.environ.get("SANDBOX_TOKEN_KEY", "default-dev-key-not-for-production")
    import base64
    key_bytes = key.encode()
    encrypted_bytes = base64.b64decode(encrypted.encode())
    decrypted = bytes(e ^ key_bytes[i % len(key_bytes)] for i, e in enumerate(encrypted_bytes))
    return decrypted.decode()


async def get_sandbox_user_token(user_id: str) -> str | None:
    """Retrieve the decrypted GitHub sandbox token for a user."""
    conn = _connection_store.get(f"sandbox:{user_id}")
    if conn and conn.get("token"):
        return _decrypt_sandbox_token(conn["token"])
    return None


async def get_todo_user_token(user_id: str, app_state=None) -> str | None:
    """Retrieve the stored Microsoft To-Do refresh token for a user.

    Called by the TodoAgent to get the user's delegated token for MCP calls.
    Falls back to Cosmos DB if not in the in-memory cache.
    """
    conn = _connection_store.get(f"todo:{user_id}")
    if conn:
        return conn.get("refreshToken")

    # Try Cosmos DB fallback
    svc = getattr(app_state, "user_profile_service", None) if app_state else None
    if svc:
        profile = await svc.get_profile(user_id)
        if profile and profile.get("todoRefreshToken"):
            # Re-populate in-memory cache
            _connection_store[f"todo:{user_id}"] = {
                "refreshToken": profile["todoRefreshToken"],
                "connectedAt": profile.get("todoConnectedAt", ""),
            }
            return profile["todoRefreshToken"]
    return None


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
    """Get profile photo — check Blob Storage, local uploads, then MS Graph."""
    user_id, _ = _get_user(request)

    # Check if user has a custom uploaded photo in Blob Storage
    if user_id:
        svc = request.app.state.user_profile_service
        if svc:
            profile = await svc.get_profile(user_id)
            if profile and profile.get("profilePhotoUrl"):
                photo_url = profile["profilePhotoUrl"]
                storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
                if (
                    storage_account
                    and f"{storage_account}.blob.core.windows.net/uploads/" in photo_url
                ):
                    try:
                        from azure.identity.aio import DefaultAzureCredential
                        from azure.storage.blob.aio import BlobServiceClient

                        blob_path = photo_url.split("/uploads/", 1)[1]
                        credential = DefaultAzureCredential()
                        blob_service = BlobServiceClient(
                            account_url=f"https://{storage_account}.blob.core.windows.net",
                            credential=credential,
                        )
                        async with blob_service:
                            blob_client = blob_service.get_container_client(
                                "uploads"
                            ).get_blob_client(blob_path)
                            download = await blob_client.download_blob()
                            photo_data = await download.readall()
                            props = await blob_client.get_blob_properties()
                            content_type = (
                                props.content_settings.content_type or "image/jpeg"
                            )
                        await credential.close()
                        return Response(content=photo_data, media_type=content_type)
                    except Exception:
                        logger.exception(
                            "Failed to fetch profile photo from Blob for user %s", user_id
                        )

        # Check for locally uploaded photo (local dev without Cosmos)
        from pathlib import Path

        upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "profile-photos"
        if upload_dir.exists():
            user_photos = sorted(
                upload_dir.glob(f"{user_id}_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if user_photos:
                photo_data = user_photos[0].read_bytes()
                ext = user_photos[0].suffix.lower().lstrip(".")
                ct = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                }
                return Response(content=photo_data, media_type=ct.get(ext, "image/jpeg"))

    # Fallback to Microsoft Graph photo (short timeout to avoid blocking UI)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=404, content={"detail": "No photo available"})

    token = auth_header[7:]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://graph.microsoft.com/v1.0/me/photo/$value",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                if resp.status == 200:
                    photo_data = await resp.read()
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    return Response(content=photo_data, media_type=content_type)
                else:
                    return JSONResponse(
                        status_code=404, content={"detail": "No photo available"}
                    )
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
            content={
                "detail": f"File too large. Maximum size: {MAX_PHOTO_SIZE // (1024 * 1024)}MB"
            },
        )

    # Try to upload to Blob Storage
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if storage_account:
        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.storage.blob.aio import BlobServiceClient

            ext = (
                file.filename.rsplit(".", 1)[-1]
                if file.filename and "." in file.filename
                else "jpg"
            )
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
                await blob_client.upload_blob(
                    content, content_type=file.content_type, overwrite=True
                )
                photo_url = f"https://{storage_account}.blob.core.windows.net/uploads/{blob_name}"

            await credential.close()

            # Update profile with photo URL
            svc = request.app.state.user_profile_service
            if svc:
                await svc.update_profile_photo_url(user_id, photo_url)

            logger.info("Uploaded profile photo for user %s: %s", user_id, blob_name)
            return {"success": True, "photoUrl": photo_url}

        except Exception:
            logger.exception(
                "Failed to upload profile photo to Blob Storage — falling back to local"
            )
            # Fall through to local storage below

    # Local dev (or Blob Storage fallback): save to uploads directory
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
