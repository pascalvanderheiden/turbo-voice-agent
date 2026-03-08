"""Request/response logging middleware with correlation ID propagation."""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import correlation_id_var, generate_correlation_id, user_id_var

logger = logging.getLogger("app.middleware.request")

# Paths to skip logging (health checks, static files)
SKIP_PATHS = {"/health"}
SKIP_PREFIXES = ("/uploads/", "/static/", "/docs", "/openapi.json", "/redoc")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log incoming requests and outgoing responses with correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip noisy endpoints
        if path in SKIP_PATHS or any(path.startswith(p) for p in SKIP_PREFIXES):
            return await call_next(request)

        # Set correlation ID from header or generate new one
        cid = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        correlation_id_var.set(cid)

        # Set user ID if available from auth middleware
        uid = getattr(request.state, "user_id", "")
        if uid:
            user_id_var.set(uid)

        start = time.perf_counter()
        method = request.method
        logger.info("→ %s %s", method, path)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Correlation-ID"] = cid
            logger.info(
                "← %s %s %d (%.0fms)",
                method, path, response.status_code, duration_ms,
            )
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("✗ %s %s failed (%.0fms)", method, path, duration_ms)
            raise
        finally:
            correlation_id_var.set("")
            user_id_var.set("")
