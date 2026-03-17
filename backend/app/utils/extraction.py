"""Content extraction utilities for PDF text and image descriptions."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_PDF_CHARS = 4000


async def extract_pdf_text(file_path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF, truncated to MAX_PDF_CHARS."""
    try:
        import pymupdf

        doc = pymupdf.open(str(file_path))
        pages: list[str] = []
        total = 0
        for page in doc:
            text = page.get_text()
            if total + len(text) > MAX_PDF_CHARS:
                pages.append(text[: MAX_PDF_CHARS - total])
                break
            pages.append(text)
            total += len(text)
        doc.close()
        result = "\n---\n".join(pages).strip()
        logger.info("Extracted %d chars from PDF %s", len(result), file_path.name)
        return result
    except Exception:
        logger.exception("Failed to extract text from PDF %s", file_path.name)
        return ""


async def extract_image_description(file_path: Path) -> str:
    """Get an AI description of an image using Mistral Document AI.

    Falls back to empty string if the Mistral endpoint is unavailable.
    """
    endpoint = os.environ.get("MISTRAL_DOCUMENT_AI_ENDPOINT", "")
    deployment = os.environ.get("MISTRAL_DOCUMENT_AI_DEPLOYMENT", "mistral-document-ai-2512")

    if not endpoint:
        logger.debug("MISTRAL_DOCUMENT_AI_ENDPOINT not set, skipping image description")
        return ""

    try:
        from openai import AsyncAzureOpenAI

        from app.agents.config import _get_token_provider

        token_provider = _get_token_provider()
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        base_url = f"{parsed.scheme}://{parsed.hostname}"

        if token_provider:
            client = AsyncAzureOpenAI(
                azure_endpoint=base_url,
                azure_ad_token_provider=token_provider,
                api_version="2025-01-01-preview",
            )
        else:
            client = AsyncAzureOpenAI(
                azure_endpoint=base_url,
                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                api_version="2025-01-01-preview",
            )

        data_b64 = base64.b64encode(file_path.read_bytes()).decode()
        ext = file_path.suffix.lstrip(".").lower()
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "image/png")

        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe this image in detail for a "
                                "product development context. "
                                "Focus on UI elements, layout, features, "
                                "colors, and any text visible. "
                                "Be concise but thorough."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data_b64}"},
                        },
                    ],
                }
            ],
            max_completion_tokens=500,
            temperature=0.3,
        )
        desc = response.choices[0].message.content or ""
        logger.info("Got Mistral description for %s (%d chars)", file_path.name, len(desc))
        return desc

    except Exception:
        logger.warning("Mistral image description failed for %s, skipping", file_path.name)
        return ""


def _resolve_upload_path(url: str) -> Path | None:
    """Resolve a /uploads/... URL to a local file path."""
    if not url:
        return None
    filename = url.split("/")[-1]
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
    path = upload_dir / filename
    return path if path.exists() else None


async def extract_attachment_context(attachments: list[str]) -> str:
    """Extract text from all PDF attachments, return combined context."""
    if not attachments:
        return ""
    parts: list[str] = []
    for url in attachments:
        path = _resolve_upload_path(url)
        if path and path.suffix.lower() == ".pdf":
            text = await extract_pdf_text(path)
            if text:
                parts.append(f"### PDF: {path.name}\n{text}")
    if not parts:
        return ""
    return "\n\n---\nAttached document content:\n" + "\n\n".join(parts)


async def extract_image_context(images: list[str]) -> str:
    """Get AI descriptions of all images in parallel, return combined context."""
    if not images:
        return ""

    async def _describe(url: str) -> str:
        path = _resolve_upload_path(url)
        if not path:
            return ""
        desc = await extract_image_description(path)
        return f"### Image: {path.name}\n{desc}" if desc else ""

    results = await asyncio.gather(*[_describe(url) for url in images])
    parts = [r for r in results if r]
    if not parts:
        return ""
    return "\n\n---\nImage analysis:\n" + "\n\n".join(parts)
