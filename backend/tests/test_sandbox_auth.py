"""Tests for sandbox authentication token handling."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _clear_connection_store():
    from app.routes.user import _connection_store

    _connection_store.clear()
    yield
    _connection_store.clear()


def test_encrypt_decrypt_roundtrip():
    """Token survives encrypt → decrypt cycle."""
    os.environ["SANDBOX_TOKEN_KEY"] = "test-encryption-key-123"
    from app.routes.user import _decrypt_sandbox_token, _encrypt_sandbox_token

    original = "ghp_ABCdef123456789"
    encrypted = _encrypt_sandbox_token(original)
    assert encrypted != original
    decrypted = _decrypt_sandbox_token(encrypted)
    assert decrypted == original


def test_encrypt_produces_base64():
    """Encrypted token is valid base64."""
    import base64

    os.environ["SANDBOX_TOKEN_KEY"] = "test-key"
    from app.routes.user import _encrypt_sandbox_token

    encrypted = _encrypt_sandbox_token("ghp_test")
    # Should not raise
    base64.b64decode(encrypted)


def test_different_keys_produce_different_output():
    """Different encryption keys produce different ciphertext."""
    from app.routes.user import _encrypt_sandbox_token

    os.environ["SANDBOX_TOKEN_KEY"] = "key-one"
    enc1 = _encrypt_sandbox_token("same-token")
    os.environ["SANDBOX_TOKEN_KEY"] = "key-two"
    enc2 = _encrypt_sandbox_token("same-token")
    assert enc1 != enc2


@pytest.mark.asyncio
async def test_get_sandbox_user_token_cache_hit_skips_cosmos():
    """Cache hit returns cached token without reading Cosmos."""
    from app.routes.user import _connection_store, _encrypt_sandbox_token, get_sandbox_user_token

    os.environ["SANDBOX_TOKEN_KEY"] = "cache-hit-key"
    _connection_store["sandbox:user-1"] = {
        "token": _encrypt_sandbox_token("ghp_cached"),
        "connectedAt": "2026-05-27T10:00:00Z",
    }
    profile_service = MagicMock()
    profile_service.get_profile = AsyncMock()

    token = await get_sandbox_user_token("user-1", profile_service)

    assert token == "ghp_cached"
    profile_service.get_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_sandbox_user_token_cache_miss_reads_cosmos_and_warms_cache():
    """Cache miss falls back to Cosmos and repopulates the process cache."""
    from app.routes.user import _connection_store, _encrypt_sandbox_token, get_sandbox_user_token

    os.environ["SANDBOX_TOKEN_KEY"] = "cosmos-key"
    encrypted = _encrypt_sandbox_token("ghp_from_cosmos")
    profile_service = MagicMock()
    profile_service.get_profile = AsyncMock(
        return_value={
            "githubSandboxToken": encrypted,
            "githubSandboxConnectedAt": "2026-05-27T10:01:00Z",
        }
    )

    token = await get_sandbox_user_token("user-2", profile_service)

    assert token == "ghp_from_cosmos"
    profile_service.get_profile.assert_awaited_once_with("user-2")
    assert _connection_store["sandbox:user-2"] == {
        "token": encrypted,
        "connectedAt": "2026-05-27T10:01:00Z",
    }


@pytest.mark.asyncio
async def test_get_sandbox_user_token_cache_miss_cosmos_has_no_token_returns_none():
    """Cache miss returns None when Cosmos has no GitHub sandbox token."""
    from app.routes.user import _connection_store, get_sandbox_user_token

    profile_service = MagicMock()
    profile_service.get_profile = AsyncMock(return_value={"githubSandboxToken": None})

    token = await get_sandbox_user_token("user-3", profile_service)

    assert token is None
    profile_service.get_profile.assert_awaited_once_with("user-3")
    assert "sandbox:user-3" not in _connection_store
