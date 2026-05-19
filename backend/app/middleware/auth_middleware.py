"""FastAPI middleware for Entra ID authentication."""

from __future__ import annotations

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import validate_token

logger = logging.getLogger(__name__)

# Paths that skip authentication
SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
SKIP_PREFIXES = ("/uploads/", "/static/", "/api/auth/callback/")

MOCK_USER = {
    "oid": "00000000-0000-0000-0000-000000000000",
    "preferred_username": "dev@example.com",
    "name": "Local Dev User",
    "tid": "local",
}


class EntraAuthMiddleware(BaseHTTPMiddleware):
    """Validate Entra ID JWT on all /api/* routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-API paths and health/docs
        if path in SKIP_PATHS or any(path.startswith(p) for p in SKIP_PREFIXES):
            return await call_next(request)

        # Live preview proxy — opened in new tab without auth headers
        if "/preview/" in path and path.startswith("/api/dev/"):
            return await call_next(request)

        # Auth disabled for local dev
        if os.environ.get("AUTH_DISABLED", "").lower() == "true":
            request.state.user_id = MOCK_USER["oid"]
            request.state.user_claims = MOCK_USER
            return await call_next(request)

        # Only protect /api/* and /ws/* paths
        if not path.startswith("/api/") and not path.startswith("/ws/"):
            return await call_next(request)

        # WebSocket auth is handled by the WS endpoint itself
        if path.startswith("/ws/"):
            return await call_next(request)

        # Extract Bearer token (header or query param for SSE/EventSource)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif request.query_params.get("token"):
            token = request.query_params["token"]
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        try:
            claims = await validate_token(token)
            request.state.user_id = claims["oid"]
            request.state.user_claims = claims
        except ValueError as e:
            logger.warning("Auth failed: %s", e)
            return JSONResponse(status_code=401, content={"detail": str(e)})
        except Exception:
            logger.exception("Unexpected auth error")
            return JSONResponse(status_code=401, content={"detail": "Authentication failed"})

        return await call_next(request)
