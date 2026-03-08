"""Research OpenAI clients — web search (gpt-4.1) and deep research (o3-deep-research).

Uses the Azure OpenAI Responses API with web_search_preview tool.
Deep research uses background mode with polling.
"""

import asyncio
import logging
import os
from urllib.parse import urlparse

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _get_api_key_or_token(key_env: str) -> dict:
    """Return api_key kwarg or set up token-based auth headers."""
    api_key = os.environ.get(key_env, "")
    if api_key:
        return {"api_key": api_key}
    # Managed identity — get token for Cognitive Services
    try:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return {"api_key": token.token}
    except Exception:
        return {"api_key": ""}


def _make_client(endpoint_env: str, key_env: str) -> AsyncOpenAI:
    endpoint = os.environ.get(endpoint_env, "")
    parsed = urlparse(endpoint)
    base_url = f"{parsed.scheme}://{parsed.hostname}/openai/v1/"
    auth = _get_api_key_or_token(key_env)
    return AsyncOpenAI(
        **auth,
        base_url=base_url,
    )


def get_web_search_client() -> AsyncOpenAI:
    """Client for gpt-4.1 web search (East US 2)."""
    return _make_client("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")


def get_deep_research_client() -> AsyncOpenAI:
    """Client for o3-deep-research (West US)."""
    return _make_client("AZURE_OPENAI_WESTUS_ENDPOINT", "AZURE_OPENAI_WESTUS_API_KEY")


def _parse_response(response) -> tuple[str, list[dict]]:
    """Extract output text and citations from a Responses API response."""
    text = ""
    citations: list[dict] = []
    seen_urls: set[str] = set()

    for item in response.output:
        if hasattr(item, "content") and item.content is not None:
            for block in item.content:
                if hasattr(block, "text"):
                    text = block.text
                if hasattr(block, "annotations"):
                    for ann in block.annotations:
                        if hasattr(ann, "url") and ann.url not in seen_urls:
                            seen_urls.add(ann.url)
                            citations.append({
                                "url": ann.url,
                                "title": getattr(ann, "title", ""),
                            })

    return text, citations


async def run_web_search(query: str) -> tuple[str, list[dict]]:
    """Run a quick web search using gpt-4.1 + web_search_preview."""
    client = get_web_search_client()
    deployment = os.environ.get("AZURE_OPENAI_SEARCH_DEPLOYMENT", "gpt-4.1")

    logger.info("Web search: model=%s, query=%s", deployment, query[:80])
    response = await client.responses.create(
        model=deployment,
        tools=[{"type": "web_search_preview"}],
        input=query,
    )
    return _parse_response(response)


async def run_deep_research(query: str) -> tuple[str, list[dict]]:
    """Run deep research using o3-deep-research + web_search_preview.

    Uses background mode: initiates the request, then polls until complete.
    Times out after 10 minutes if the model never starts processing.
    """
    client = get_deep_research_client()
    deployment = os.environ.get("AZURE_OPENAI_DEEP_RESEARCH_DEPLOYMENT", "o3-deep-research")

    logger.info("Deep research (background): model=%s, query=%s", deployment, query[:80])

    # Start background task
    response = await client.responses.create(
        model=deployment,
        tools=[{"type": "web_search_preview"}],
        input=query,
        background=True,
    )
    logger.info("Deep research started: id=%s, status=%s", response.id, response.status)

    # Poll until complete (max 20 minutes)
    poll_count = 0
    max_polls = 120  # 120 * ~10s = ~20 minutes
    while response.status in ("queued", "in_progress"):
        poll_count += 1
        if poll_count > max_polls:
            logger.error("Deep research timed out after %d polls (id=%s, status=%s)", poll_count, response.id, response.status)
            if response.status == "queued":
                raise RuntimeError(
                    "Deep research timed out — the model stayed queued for too long. "
                    "This may indicate insufficient capacity on the o3-deep-research deployment."
                )
            raise RuntimeError(
                "Deep research timed out after 20 minutes of processing. "
                "The model was actively working but didn't complete in time."
            )
        wait_time = min(10, 3 + poll_count)  # ramp from 3s to 10s
        logger.info("Deep research polling #%d: status=%s (waiting %ds)", poll_count, response.status, wait_time)
        await asyncio.sleep(wait_time)
        response = await client.responses.retrieve(response.id)

    logger.info("Deep research finished: id=%s, status=%s", response.id, response.status)

    if response.status == "failed":
        error = getattr(response, "error", None)
        raise RuntimeError(f"Deep research failed: {error}")

    if response.status == "cancelled":
        raise RuntimeError("Deep research was cancelled")

    return _parse_response(response)
