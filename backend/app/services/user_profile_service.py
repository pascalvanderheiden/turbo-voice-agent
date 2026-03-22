"""Cosmos DB-backed user profile service."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)


class UserProfileService:
    """Manage user profiles in Cosmos DB."""

    def __init__(self, container: ContainerProxy):
        self._container = container

    async def upsert_on_login(self, user_id: str, display_name: str, email: str) -> dict[str, Any]:
        """Create or update profile on login. Returns the profile."""
        now = datetime.utcnow().isoformat()
        # Try to get existing profile
        try:
            existing = await self._container.read_item(item=user_id, partition_key=user_id)
            # Update last login and basic info
            existing["displayName"] = display_name
            existing["email"] = email
            existing["lastLoginAt"] = now
            await self._container.upsert_item(existing)
            return existing
        except Exception:
            # Create new profile
            profile = {
                "id": user_id,
                "userId": user_id,
                "displayName": display_name,
                "email": email,
                "locale": "en",
                "avatarUrl": None,
                "profilePhotoUrl": None,
                "lastLoginAt": now,
                "premiumUsage": {},
                "premiumTotal": 0,
            }
            await self._container.upsert_item(profile)
            return profile

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        """Get user profile by ID."""
        try:
            return await self._container.read_item(item=user_id, partition_key=user_id)
        except Exception:
            return None

    async def update_locale(self, user_id: str, locale: str) -> dict[str, Any] | None:
        """Update the user's locale preference."""
        try:
            profile = await self._container.read_item(item=user_id, partition_key=user_id)
            profile["locale"] = locale
            await self._container.upsert_item(profile)
            return profile
        except Exception:
            return None

    async def update_sandbox_token(
        self, user_id: str, token: str | None, connected_at: str | None
    ) -> dict[str, Any] | None:
        """Persist or clear the GitHub sandbox PAT on the user profile."""
        try:
            profile = await self._container.read_item(item=user_id, partition_key=user_id)
            profile["githubSandboxToken"] = token
            profile["githubSandboxConnectedAt"] = connected_at
            await self._container.upsert_item(profile)
            logger.info("Updated sandbox token for user %s", user_id)
            return profile
        except Exception:
            logger.exception("Failed to update sandbox token for user %s", user_id)
            return None

    async def update_todo_connection(
        self, user_id: str, refresh_token: str | None, connected_at: str | None
    ) -> dict[str, Any] | None:
        """Persist or clear the Microsoft To-Do refresh token on the user profile."""
        try:
            profile = await self._container.read_item(item=user_id, partition_key=user_id)
            profile["todoRefreshToken"] = refresh_token
            profile["todoConnectedAt"] = connected_at
            await self._container.upsert_item(profile)
            logger.info("Updated To-Do connection for user %s", user_id)
            return profile
        except Exception:
            logger.exception("Failed to update To-Do connection for user %s", user_id)
            return None

    async def update_work_connection(
        self, user_id: str, refresh_token: str | None, connected_at: str | None
    ) -> dict[str, Any] | None:
        """Persist or clear the Work Account refresh token on the user profile."""
        try:
            profile = await self._container.read_item(item=user_id, partition_key=user_id)
            profile["workRefreshToken"] = refresh_token
            profile["workConnectedAt"] = connected_at
            await self._container.upsert_item(profile)
            logger.info("Updated Work Account connection for user %s", user_id)
            return profile
        except Exception:
            logger.exception("Failed to update Work connection for user %s", user_id)
            return None

    async def update_profile_photo_url(
        self, user_id: str, photo_url: str
    ) -> dict[str, Any] | None:
        """Update the user's profile photo URL."""
        try:
            profile = await self._container.read_item(item=user_id, partition_key=user_id)
            profile["profilePhotoUrl"] = photo_url
            await self._container.upsert_item(profile)
            logger.info("Updated profile photo for user %s", user_id)
            return profile
        except Exception:
            # Profile may not exist yet — create it with the photo URL
            try:
                now = datetime.now(UTC).isoformat()
                profile = {
                    "id": user_id,
                    "userId": user_id,
                    "displayName": "",
                    "email": "",
                    "locale": "en",
                    "avatarUrl": None,
                    "profilePhotoUrl": photo_url,
                    "lastLoginAt": now,
                    "premiumUsage": {},
                    "premiumTotal": 0,
                }
                await self._container.upsert_item(profile)
                logger.info("Created profile with photo for user %s", user_id)
                return profile
            except Exception:
                logger.exception(
                    "Failed to update profile photo for user %s", user_id
                )
                return None

    async def record_premium_usage(
        self, user_id: str, count: int
    ) -> dict[str, Any] | None:
        """Persist the premium request total, updating per-month usage.

        *count* is the new cumulative total.  We compute the delta from the
        stored ``premiumTotal`` and add it to the current month bucket.
        """
        month_key = datetime.now(UTC).strftime("%Y-%m")
        try:
            profile = await self._container.read_item(
                item=user_id, partition_key=user_id
            )
            usage: dict = profile.get("premiumUsage") or {}
            prev_total: int = profile.get("premiumTotal") or 0
            delta = max(0, count - prev_total)
            if delta > 0:
                usage[month_key] = usage.get(month_key, 0) + delta
            profile["premiumUsage"] = usage
            profile["premiumTotal"] = count
            await self._container.upsert_item(profile)
            return profile
        except Exception:
            logger.exception(
                "Failed to record premium usage for user %s", user_id
            )
            return None

    async def get_premium_usage(
        self, user_id: str
    ) -> dict[str, Any]:
        """Return ``{total, usage: {month: count}}``."""
        try:
            profile = await self._container.read_item(
                item=user_id, partition_key=user_id
            )
            return {
                "total": profile.get("premiumTotal", 0),
                "usage": profile.get("premiumUsage", {}),
            }
        except Exception:
            return {"total": 0, "usage": {}}
