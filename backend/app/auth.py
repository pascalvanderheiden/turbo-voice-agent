"""Entra ID JWT validation using JWKS public keys."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import aiohttp
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: float = 0
_JWKS_CACHE_TTL = 86400  # 24 hours


async def _fetch_jwks(tenant_id: str) -> dict[str, Any]:
    """Fetch JWKS keys from Entra ID, with 24h cache."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache
    url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to fetch JWKS: HTTP {resp.status}")
            data = await resp.json()
            _jwks_cache = data
            _jwks_cache_time = now
            logger.info("Fetched JWKS keys from Entra ID (tenant=%s)", tenant_id)
            return data


async def validate_token(token: str) -> dict[str, Any]:
    """Validate an Entra ID access token and return claims.

    Raises ValueError on invalid/expired/wrong audience tokens.
    """
    tenant_id = os.environ.get("ENTRA_TENANT_ID", "")
    client_id = os.environ.get("ENTRA_CLIENT_ID", "")
    if not tenant_id or not client_id:
        raise ValueError("ENTRA_TENANT_ID and ENTRA_CLIENT_ID must be set")

    jwks = await _fetch_jwks(tenant_id)

    # Decode header to find the signing key
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError(f"Invalid token header: {e}")

    kid = unverified_header.get("kid")
    rsa_key = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise ValueError("Token signing key not found in JWKS")

    try:
        claims = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=[
                f"api://{client_id}",
                f"api://{client_id}/access",
                client_id,
            ],
            issuer=[
                f"https://sts.windows.net/{tenant_id}/",
                f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            ],
        )
    except JWTError as e:
        raise ValueError(f"Token validation failed: {e}")

    # Validate tenant
    if claims.get("tid") != tenant_id:
        raise ValueError("Token is from wrong tenant")

    return claims
