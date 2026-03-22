"""WorkIQ MCP client — queries Microsoft 365 workplace data via WorkIQ."""

from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Stub response for local development (AUTH_DISABLED mode)
_STUB_RESPONSE = (
    "Based on your recent emails and meetings, here's a summary: "
    "You have 3 upcoming meetings today, 12 unread emails (2 flagged), "
    "and a document shared by your team lead awaiting review. "
    "Your next meeting is 'Sprint Planning' in 45 minutes."
)


class WorkMcpClient:
    """Client that queries Microsoft 365 workplace data via WorkIQ.

    When a real user token (refresh token) is provided, it exchanges it for
    an access token and calls the WorkIQ ask endpoint.  When ``user_token``
    is a mock value (local dev), falls back to a stub response.
    """

    def __init__(self) -> None:
        self._healthy = True
        self._client_id = os.environ.get("WORKIQ_OAUTH_CLIENT_ID") or os.environ.get(
            "ENTRA_CLIENT_ID", ""
        )
        self._client_secret = os.environ.get("ENTRA_CLIENT_SECRET", "")
        self._tenant_id = os.environ.get("WORKIQ_OAUTH_TENANT_ID", "common")

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    async def health_check(self) -> bool:
        return self._healthy

    async def _get_access_token(self, refresh_token: str) -> str | None:
        """Exchange a refresh token for a fresh access token."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "scope": "offline_access Mail.Read Calendars.Read Files.Read.All Chat.Read User.Read",
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("WorkIQ token refresh failed (%d): %s", resp.status, body)
                        return None
                    tokens = await resp.json()
                    return tokens.get("access_token")
        except Exception:
            logger.exception("WorkIQ token refresh request failed")
            return None

    async def ask(
        self,
        question: str,
        user_token: str | None = None,
        file_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ask a work-related question via WorkIQ.

        Returns dict with 'response' (answer text) and 'conversationId'.
        """
        if not user_token:
            return {
                "error": "Work account is not connected. "
                "Please authenticate in your profile settings."
            }

        logger.info("WorkIQ ask: question=%s (has_token=%s)", question[:80], bool(user_token))

        # Local dev mock mode
        if user_token == "mock-token-auth-disabled":
            return await self._stub_ask(question)

        # Real WorkIQ mode
        access_token = await self._get_access_token(user_token)
        if not access_token:
            return {"error": "Failed to refresh access token. Please reconnect your work account."}

        return await self._workiq_ask(question, access_token, file_urls)

    async def _workiq_ask(
        self,
        question: str,
        access_token: str,
        file_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """Call WorkIQ ask_work_iq endpoint."""
        try:
            payload: dict[str, Any] = {"question": question}
            if file_urls:
                payload["fileUrls"] = file_urls

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://workiq.microsoft.com/api/ask",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("WorkIQ ask failed (%d): %s", resp.status, body)
                        return {"error": f"WorkIQ error ({resp.status}): {body}"}
                    result = await resp.json()
                    return {
                        "response": result.get("response", ""),
                        "conversationId": result.get("conversationId", ""),
                    }
        except Exception:
            logger.exception("WorkIQ ask request failed")
            return {"error": "WorkIQ request failed. Please try again."}

    async def _stub_ask(self, question: str) -> dict[str, Any]:
        """Stub response for local dev (AUTH_DISABLED mode)."""
        return {
            "response": f"[Mock WorkIQ] Regarding '{question[:60]}': {_STUB_RESPONSE}",
            "conversationId": "mock-conversation-001",
        }

    async def start(self) -> None:
        logger.info("WorkMcpClient: started")
        self._healthy = True

    async def stop(self) -> None:
        logger.info("WorkMcpClient: stop")
        self._healthy = False
