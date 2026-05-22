"""Unit tests for ``SessionSandboxClient``.

Covers URL composition, identifier propagation, bearer-token attachment, retry on
401 with token refresh, SSE streaming, and ``stop_session`` 404 tolerance. The
Azure credential is mocked — no real Azure calls are made.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from azure.core.credentials import AccessToken

from app.services.session_sandbox_client import (
    SESSION_API_VERSION,
    SessionSandboxClient,
)

ENDPOINT = "https://pool.example.com"


def _mock_credential(token: str = "tok-initial") -> MagicMock:
    """Return a mock TokenCredential whose get_token returns a fresh AccessToken."""
    cred = MagicMock()
    cred.get_token.return_value = AccessToken(token, int(time.time()) + 3600)
    return cred


@pytest.fixture
def credential() -> MagicMock:
    return _mock_credential()


@pytest.fixture
def client(credential: MagicMock) -> SessionSandboxClient:
    return SessionSandboxClient(endpoint=ENDPOINT, credential=credential)


# ── construction ────────────────────────────────────────────────────────


def test_init_requires_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SESSION_POOL_MANAGEMENT_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_POOL_MANAGEMENT_ENDPOINT"):
        SessionSandboxClient(credential=_mock_credential())


def test_init_reads_endpoint_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSION_POOL_MANAGEMENT_ENDPOINT", "https://from-env.example.com/")
    c = SessionSandboxClient(credential=_mock_credential())
    assert c._endpoint == "https://from-env.example.com"  # trailing slash stripped


# ── request: URL composition, identifier, token ────────────────────────


@respx.mock
async def test_request_composes_url_with_identifier_and_api_version(
    client: SessionSandboxClient,
) -> None:
    route = respx.get(f"{ENDPOINT}/tasks").mock(return_value=httpx.Response(200, json={"ok": True}))

    resp = await client.request("GET", "/tasks", identifier="task-123")

    assert resp.status_code == 200
    assert route.called
    sent = route.calls.last.request
    assert sent.url.params["identifier"] == "task-123"
    assert sent.url.params["api-version"] == SESSION_API_VERSION


@respx.mock
async def test_request_attaches_bearer_token(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    credential.get_token.return_value = AccessToken("my-bearer", int(time.time()) + 3600)
    respx.get(f"{ENDPOINT}/health").mock(return_value=httpx.Response(200))

    await client.request("GET", "/health", identifier="t1")

    sent = respx.calls.last.request
    assert sent.headers["authorization"] == "Bearer my-bearer"


@respx.mock
async def test_request_forwards_json_body_and_caller_headers(
    client: SessionSandboxClient,
) -> None:
    route = respx.post(f"{ENDPOINT}/tasks").mock(return_value=httpx.Response(201))

    await client.request(
        "POST",
        "/tasks",
        identifier="t1",
        json={"hello": "world"},
        headers={"X-GH-Token": "ghs_abc"},
    )

    sent = route.calls.last.request
    assert b'"hello"' in sent.content
    assert sent.headers["x-gh-token"] == "ghs_abc"
    # auth header still wins:
    assert sent.headers["authorization"].startswith("Bearer ")


@respx.mock
async def test_request_caller_cannot_override_routing_params(
    client: SessionSandboxClient,
) -> None:
    respx.get(f"{ENDPOINT}/tasks").mock(return_value=httpx.Response(200))

    await client.request(
        "GET",
        "/tasks",
        identifier="real-id",
        params={"identifier": "spoof", "api-version": "bogus", "extra": "kept"},
    )

    sent = respx.calls.last.request
    assert sent.url.params["identifier"] == "real-id"
    assert sent.url.params["api-version"] == SESSION_API_VERSION
    assert sent.url.params["extra"] == "kept"


@respx.mock
async def test_request_normalises_path_without_leading_slash(
    client: SessionSandboxClient,
) -> None:
    route = respx.get(f"{ENDPOINT}/files/foo.txt").mock(return_value=httpx.Response(200))

    await client.request("GET", "files/foo.txt", identifier="t1")

    assert route.called


# ── request: retry on 401/403 ──────────────────────────────────────────


@respx.mock
async def test_request_retries_once_on_401_with_token_refresh(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    credential.get_token.side_effect = [
        AccessToken("stale-token", int(time.time()) + 3600),
        AccessToken("fresh-token", int(time.time()) + 3600),
    ]
    route = respx.get(f"{ENDPOINT}/tasks").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json={"ok": True})]
    )

    resp = await client.request("GET", "/tasks", identifier="t1")

    assert resp.status_code == 200
    assert route.call_count == 2
    assert credential.get_token.call_count == 2
    # First call had stale token, retry had fresh token
    first_call, second_call = route.calls
    assert first_call.request.headers["authorization"] == "Bearer stale-token"
    assert second_call.request.headers["authorization"] == "Bearer fresh-token"


@respx.mock
async def test_request_retries_once_on_403(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    route = respx.get(f"{ENDPOINT}/tasks").mock(
        side_effect=[httpx.Response(403), httpx.Response(200)]
    )

    resp = await client.request("GET", "/tasks", identifier="t1")

    assert resp.status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_request_does_not_retry_a_second_auth_failure(
    client: SessionSandboxClient,
) -> None:
    route = respx.get(f"{ENDPOINT}/tasks").mock(
        side_effect=[httpx.Response(401), httpx.Response(401)]
    )

    resp = await client.request("GET", "/tasks", identifier="t1")

    # Second 401 is returned unchanged — exactly two attempts, no third.
    assert resp.status_code == 401
    assert route.call_count == 2


@respx.mock
async def test_request_does_not_retry_other_statuses(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    route = respx.get(f"{ENDPOINT}/tasks").mock(return_value=httpx.Response(500))

    resp = await client.request("GET", "/tasks", identifier="t1")

    assert resp.status_code == 500
    assert route.call_count == 1
    assert credential.get_token.call_count == 1  # no refresh


# ── token cache ────────────────────────────────────────────────────────


@respx.mock
async def test_token_is_cached_across_requests(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    respx.get(f"{ENDPOINT}/a").mock(return_value=httpx.Response(200))
    respx.get(f"{ENDPOINT}/b").mock(return_value=httpx.Response(200))

    await client.request("GET", "/a", identifier="t1")
    await client.request("GET", "/b", identifier="t1")

    # Only one token acquisition — cached for the second call.
    assert credential.get_token.call_count == 1


@respx.mock
async def test_expired_token_is_refreshed(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    # First token expires now (well within 60s buffer → counts as stale)
    credential.get_token.side_effect = [
        AccessToken("expired", int(time.time())),
        AccessToken("renewed", int(time.time()) + 3600),
    ]
    respx.get(f"{ENDPOINT}/a").mock(return_value=httpx.Response(200))
    respx.get(f"{ENDPOINT}/b").mock(return_value=httpx.Response(200))

    await client.request("GET", "/a", identifier="t1")
    await client.request("GET", "/b", identifier="t1")

    assert credential.get_token.call_count == 2
    assert respx.calls[-1].request.headers["authorization"] == "Bearer renewed"


# ── stream ──────────────────────────────────────────────────────────────


@respx.mock
async def test_stream_yields_sse_chunks_with_accept_header(
    client: SessionSandboxClient,
) -> None:
    body = b"data: one\n\ndata: two\n\ndata: three\n\n"
    route = respx.get(f"{ENDPOINT}/tasks/t1/stream").mock(
        return_value=httpx.Response(
            200,
            content=body,
            headers={"content-type": "text/event-stream"},
        )
    )

    chunks: list[bytes] = []
    async for chunk in client.stream("/tasks/t1/stream", identifier="t1"):
        chunks.append(chunk)

    assert route.called
    sent = route.calls.last.request
    assert sent.headers["accept"] == "text/event-stream"
    assert sent.url.params["identifier"] == "t1"
    assert sent.url.params["api-version"] == SESSION_API_VERSION
    assert sent.headers["authorization"].startswith("Bearer ")
    # Total bytes match the body even if respx delivers in one or more chunks.
    assert b"".join(chunks) == body


@respx.mock
async def test_stream_retries_once_on_401(
    client: SessionSandboxClient, credential: MagicMock
) -> None:
    credential.get_token.side_effect = [
        AccessToken("stale", int(time.time()) + 3600),
        AccessToken("fresh", int(time.time()) + 3600),
    ]
    route = respx.get(f"{ENDPOINT}/stream").mock(
        side_effect=[
            httpx.Response(401),
            httpx.Response(200, content=b"data: hi\n\n"),
        ]
    )

    chunks = [c async for c in client.stream("/stream", identifier="t1")]

    assert route.call_count == 2
    assert credential.get_token.call_count == 2
    assert b"".join(chunks) == b"data: hi\n\n"


@respx.mock
async def test_stream_caller_can_override_accept(
    client: SessionSandboxClient,
) -> None:
    route = respx.get(f"{ENDPOINT}/raw").mock(return_value=httpx.Response(200, content=b"binary"))

    chunks = [
        c
        async for c in client.stream(
            "/raw", identifier="t1", headers={"Accept": "application/octet-stream"}
        )
    ]

    sent = route.calls.last.request
    assert sent.headers["accept"] == "application/octet-stream"
    assert b"".join(chunks) == b"binary"


# ── stop_session ───────────────────────────────────────────────────────


@respx.mock
async def test_stop_session_posts_to_management_endpoint(
    client: SessionSandboxClient,
) -> None:
    route = respx.post(f"{ENDPOINT}/.management/stopSession").mock(return_value=httpx.Response(200))

    await client.stop_session("task-42")

    assert route.called
    sent = route.calls.last.request
    assert sent.method == "POST"
    assert sent.url.params["identifier"] == "task-42"
    assert sent.url.params["api-version"] == SESSION_API_VERSION
    assert sent.headers["authorization"].startswith("Bearer ")


@respx.mock
async def test_stop_session_tolerates_404(client: SessionSandboxClient) -> None:
    respx.post(f"{ENDPOINT}/.management/stopSession").mock(return_value=httpx.Response(404))

    # Must not raise.
    await client.stop_session("already-gone")


@respx.mock
async def test_stop_session_raises_on_other_errors(
    client: SessionSandboxClient,
) -> None:
    respx.post(f"{ENDPOINT}/.management/stopSession").mock(return_value=httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        await client.stop_session("boom")
