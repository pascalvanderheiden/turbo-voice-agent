"""SessionSandboxClient — httpx wrapper for Azure Container Apps dynamic session pools.

Routes sandbox HTTP traffic through a session-pool management endpoint, authenticated
with the backend's managed identity (``DefaultAzureCredential``). Caller paths are
forwarded verbatim with ``?identifier={taskId}&api-version=2025-02-02-preview`` appended.

This module is Phase 2 of the ``sandbox-dynamic-sessions`` OpenSpec change: it adds
the new client without touching the existing ACI/shared-CA implementations. Wiring
into ``sandbox_service.py`` and removal of the old code happen in later phases.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

import httpx
from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import DefaultAzureCredential

log = logging.getLogger(__name__)
# Backwards-compatible alias — earlier code in this module referenced ``logger``.
logger = log

SESSION_API_VERSION = "2025-02-02-preview"
SESSION_SCOPE = "https://dynamicsessions.io/.default"
TOKEN_REFRESH_BUFFER_SECONDS = 60

# Prefix used for log records that should be picked up as App Insights custom
# events. The backend does not currently wire opencensus / azure-monitor into
# its lifespan, so we surface custom-event semantics as structured log records
# with this prefix in ``event``. A future App Insights handler can filter on
# ``record.event.startswith("sandbox.")`` and re-emit as ``track_event``.
APPINSIGHTS_EVENT_PREFIX = "sandbox."

# Local-dev fallback: when SESSION_POOL_MANAGEMENT_ENDPOINT is unset, sandbox
# calls are routed at this base URL (the docker-compose ``sandbox`` service).
LOCAL_SANDBOX_URL_DEFAULT = "http://sandbox:3000"


class SandboxClient(Protocol):
    """Common interface implemented by both the session-pool and local-dev clients.

    All sandbox HTTP code paths in ``sandbox_service`` / ``dev_agent`` / routes
    funnel through this Protocol so the runtime backend (Azure session pool vs
    local docker-compose container) is interchangeable.
    """

    async def request(
        self,
        method: str,
        path: str,
        *,
        identifier: str,
        **kwargs: Any,
    ) -> httpx.Response: ...

    def stream_response(
        self,
        method: str,
        path: str,
        *,
        identifier: str,
        **kwargs: Any,
    ) -> Any:  # AsyncContextManager[httpx.Response]
        ...

    async def stop_session(self, identifier: str, *, reason: str = ...) -> None: ...


class SessionSandboxClient:
    """Async HTTP client for Container Apps dynamic-session pools.

    Wraps :class:`httpx.AsyncClient`, prepends the pool management endpoint, injects
    the Bearer token from ``DefaultAzureCredential``, and appends ``identifier`` +
    ``api-version`` query params on every call. Callers pass logical paths (e.g.
    ``/tasks``, ``/files/foo.txt``) unchanged — they are forwarded to the session
    container's HTTP port by the pool.

    Construct with explicit ``endpoint`` and ``credential`` for tests; production
    code constructs with no args (reads ``SESSION_POOL_MANAGEMENT_ENDPOINT`` from
    the environment and uses ``DefaultAzureCredential``).
    """

    def __init__(
        self,
        endpoint: str | None = None,
        credential: TokenCredential | None = None,
    ) -> None:
        resolved = (
            endpoint if endpoint is not None else os.getenv("SESSION_POOL_MANAGEMENT_ENDPOINT", "")
        )
        if not resolved:
            raise RuntimeError(
                "SESSION_POOL_MANAGEMENT_ENDPOINT is not configured; "
                "SessionSandboxClient cannot be initialised."
            )
        self._endpoint = resolved.rstrip("/")
        self._credential: TokenCredential = credential or DefaultAzureCredential()
        self._token: AccessToken | None = None
        # Tracks identifiers we've already emitted ``sandbox.session.allocated``
        # for. The session pool itself allocates implicitly on first request, so
        # we treat the first successful response as the allocation event.
        self._allocated: set[str] = set()

    # ── token cache ────────────────────────────────────────────────────

    def _token_is_fresh(self) -> bool:
        return (
            self._token is not None
            and self._token.expires_on - TOKEN_REFRESH_BUFFER_SECONDS > time.time()
        )

    def _get_token(self, *, force_refresh: bool = False) -> str:
        """Return a cached bearer token, refreshing if expired or forced."""
        if force_refresh or not self._token_is_fresh():
            self._token = self._credential.get_token(SESSION_SCOPE)
        assert self._token is not None  # for type checkers
        return self._token.token

    # ── URL / param / header helpers ──────────────────────────────────

    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._endpoint}{path}"

    @staticmethod
    def _merge_params(identifier: str, extra: dict[str, Any] | None) -> dict[str, Any]:
        params: dict[str, Any] = dict(extra or {})
        # The session-pool routing params are non-negotiable — never let callers
        # override them.
        params["identifier"] = identifier
        params["api-version"] = SESSION_API_VERSION
        return params

    @staticmethod
    def _merge_headers(token: str, extra: dict[str, str] | None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if extra:
            for k, v in extra.items():
                if k.lower() == "authorization":
                    continue
                headers[k] = v
        headers["Authorization"] = f"Bearer {token}"
        return headers

    # ── public API ─────────────────────────────────────────────────────

    async def request(
        self,
        method: str,
        path: str,
        *,
        identifier: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a single request, with auth + identifier query-param injection.

        On a 401/403 response the cached token is force-refreshed and the request
        is retried exactly once. A second auth failure is returned to the caller
        unchanged (status_code 401/403 on the response).

        Callers may pass ``headers={"X-GH-Token": <pat>}`` on the first request
        per session — the sandbox container middleware uses it to bootstrap
        ``gh auth login --with-token`` and ignores the header on subsequent
        requests within the same session (Phase 6 of sandbox-dynamic-sessions).
        """
        url = self._build_url(path)
        caller_params = kwargs.pop("params", None)
        caller_headers = kwargs.pop("headers", None)
        params = self._merge_params(identifier, caller_params)

        method_upper = method.upper()
        async with httpx.AsyncClient() as client:
            response: httpx.Response | None = None
            retry_count = 0
            t_start = time.monotonic()
            for attempt in (0, 1):
                token = self._get_token(force_refresh=attempt == 1)
                headers = self._merge_headers(token, caller_headers)
                response = await client.request(
                    method_upper, url, params=params, headers=headers, **kwargs
                )
                if response.status_code in (401, 403) and attempt == 0:
                    retry_count = 1
                    log.warning(
                        "sandbox.session.error",
                        extra={
                            "event": "sandbox.session.error",
                            "identifier": identifier,
                            "status_code": response.status_code,
                            "error_class": "auth_retry",
                            "method": method_upper,
                            "path": path,
                        },
                    )
                    continue
                break

            assert response is not None
            latency_ms = int((time.monotonic() - t_start) * 1000)

            # First successful response per identifier = allocation event.
            if response.status_code < 400 and identifier not in self._allocated:
                self._allocated.add(identifier)
                log.info(
                    "sandbox.session.allocated",
                    extra={
                        "event": "sandbox.session.allocated",
                        "identifier": identifier,
                        "latency_ms": latency_ms,
                        "status_code": response.status_code,
                        "retry_count": retry_count,
                    },
                )

            log.debug(
                "sandbox.session.request",
                extra={
                    "event": "sandbox.session.request",
                    "identifier": identifier,
                    "method": method_upper,
                    "path": path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "retry_count": retry_count,
                },
            )

            if response.status_code >= 400:
                log.warning(
                    "sandbox.session.error",
                    extra={
                        "event": "sandbox.session.error",
                        "identifier": identifier,
                        "status_code": response.status_code,
                        "error_class": f"http_{response.status_code}",
                        "method": method_upper,
                        "path": path,
                    },
                )

            return response

    async def stream(
        self,
        path: str,
        *,
        identifier: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> AsyncIterator[bytes]:
        """Stream a response (e.g. SSE) from the session pool.

        Yields raw chunks as they arrive. Sets ``Accept: text/event-stream`` by
        default; callers may override via ``headers=``. Auth retry semantics match
        :meth:`request` (single retry on 401/403 with token refresh).
        """
        url = self._build_url(path)
        caller_params = kwargs.pop("params", None)
        caller_headers = kwargs.pop("headers", None)
        params = self._merge_params(identifier, caller_params)

        sse_defaults = {"Accept": "text/event-stream"}
        merged_caller_headers = {**sse_defaults, **(caller_headers or {})}

        async with httpx.AsyncClient() as client:
            for attempt in (0, 1):
                token = self._get_token(force_refresh=attempt == 1)
                headers = self._merge_headers(token, merged_caller_headers)
                async with client.stream(
                    method, url, params=params, headers=headers, **kwargs
                ) as response:
                    if response.status_code in (401, 403) and attempt == 0:
                        logger.debug(
                            "Session pool stream returned %s — refreshing token and retrying",
                            response.status_code,
                        )
                        continue
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
                    return

    @asynccontextmanager
    async def stream_response(
        self,
        method: str,
        path: str,
        *,
        identifier: str,
        timeout: httpx.Timeout | float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        """Open a streaming HTTP response and yield the ``httpx.Response`` to the caller.

        Used by SSE consumers that need ``aiter_lines()`` rather than raw bytes.
        Auth retry on 401/403 happens transparently; if the retry succeeds the
        retried response is the one yielded to the caller.
        """
        url = self._build_url(path)
        caller_params = kwargs.pop("params", None)
        caller_headers = kwargs.pop("headers", None)
        params = self._merge_params(identifier, caller_params)
        client_kwargs: dict[str, Any] = {}
        if timeout is not None:
            client_kwargs["timeout"] = timeout

        async with httpx.AsyncClient(**client_kwargs) as client:
            for attempt in (0, 1):
                token = self._get_token(force_refresh=attempt == 1)
                headers = self._merge_headers(token, caller_headers)
                stream_ctx = client.stream(method, url, params=params, headers=headers, **kwargs)
                response = await stream_ctx.__aenter__()
                try:
                    if response.status_code in (401, 403) and attempt == 0:
                        logger.debug(
                            "Session pool stream returned %s — refreshing token and retrying",
                            response.status_code,
                        )
                        await stream_ctx.__aexit__(None, None, None)
                        continue
                    yield response
                    await stream_ctx.__aexit__(None, None, None)
                    return
                except BaseException:
                    await stream_ctx.__aexit__(None, None, None)
                    raise

    async def stop_session(self, identifier: str, *, reason: str = "complete") -> None:
        """Explicitly stop a session by identifier.

        Tolerates a 404 (session already gone after cooldown or prior stop). Any
        other non-success status is raised via ``raise_for_status()``. ``reason``
        is propagated to the ``sandbox.session.stopped`` event for dashboarding
        (``cancel`` | ``complete`` | ``disconnect``).
        """
        response = await self.request("POST", "/.management/stopSession", identifier=identifier)
        if response.status_code == 404:
            log.debug("stop_session: session %s already gone (404, tolerated)", identifier)
        else:
            response.raise_for_status()
        # Drop allocation tracking so a future re-use re-emits ``allocated``.
        self._allocated.discard(identifier)
        log.info(
            "sandbox.session.stopped",
            extra={
                "event": "sandbox.session.stopped",
                "identifier": identifier,
                "status_code": response.status_code,
                "reason": reason,
            },
        )


class LocalSandboxClient:
    """Thin :class:`SandboxClient` implementation for docker-compose local development.

    Selected automatically by :func:`get_sandbox_client` when
    ``SESSION_POOL_MANAGEMENT_ENDPOINT`` is unset. Routes every call to a single
    long-running sandbox container (``http://sandbox:3000`` by default), ignoring
    the ``identifier`` parameter — local dev has no per-task isolation. The API
    surface mirrors :class:`SessionSandboxClient` so callers don't branch.

    The ``SANDBOX_URL`` env var overrides the base URL (legacy compose setups
    use ``http://localhost:4000``).
    """

    def __init__(self, base_url: str | None = None) -> None:
        resolved = (
            base_url
            if base_url is not None
            else os.getenv("SANDBOX_URL", LOCAL_SANDBOX_URL_DEFAULT)
        )
        self._base_url = resolved.rstrip("/")

    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        identifier: str,  # noqa: ARG002 — ignored in local mode (no per-task isolation)
        **kwargs: Any,
    ) -> httpx.Response:
        url = self._build_url(path)
        timeout = kwargs.pop("timeout", 30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(method, url, **kwargs)

    @asynccontextmanager
    async def stream_response(
        self,
        method: str,
        path: str,
        *,
        identifier: str,  # noqa: ARG002 — ignored in local mode
        timeout: httpx.Timeout | float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        url = self._build_url(path)
        client_kwargs: dict[str, Any] = {}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        async with httpx.AsyncClient(**client_kwargs) as client:
            async with client.stream(method, url, **kwargs) as response:
                yield response

    async def stop_session(
        self,
        identifier: str,  # noqa: ARG002 — no-op locally
        *,
        reason: str = "complete",  # noqa: ARG002 — no-op locally
    ) -> None:
        """No-op in local-dev mode: the shared container is long-running.

        Per-task cleanup is handled by :meth:`request` calls to
        ``DELETE /tasks/{sandbox_task_id}`` from the dev agent.
        """
        logger.debug(
            "LocalSandboxClient.stop_session: no-op (local docker-compose has no sessions)"
        )


# ── module-level factory ──────────────────────────────────────────────

_client_singleton: SandboxClient | None = None


def get_sandbox_client() -> SandboxClient:
    """Return the process-wide sandbox client, instantiated lazily.

    Feature-detection: if ``SESSION_POOL_MANAGEMENT_ENDPOINT`` is set, returns
    :class:`SessionSandboxClient`; otherwise returns :class:`LocalSandboxClient`.
    No ``USE_*`` flag — the deploy-time env determines the runtime.
    """
    global _client_singleton
    if _client_singleton is None:
        if os.getenv("SESSION_POOL_MANAGEMENT_ENDPOINT"):
            _client_singleton = SessionSandboxClient()
            logger.info("Sandbox client: SessionSandboxClient (Azure session pool)")
        else:
            _client_singleton = LocalSandboxClient()
            logger.info(
                "Sandbox client: LocalSandboxClient (docker-compose at %s)",
                getattr(_client_singleton, "_base_url", "?"),
            )
    return _client_singleton


def reset_sandbox_client() -> None:
    """Reset the cached singleton — used by tests that swap env vars."""
    global _client_singleton
    _client_singleton = None
