"""Slides Agent — specialist agent for presentation CRUD and refinement."""

import base64
import json
import logging
import os
from pathlib import Path

from openai import AsyncAzureOpenAI

from app.models.slides import SlidesCreate, SlidesUpdate
from app.services.memory_slides_service import InMemorySlidesService
from app.utils.extraction import extract_attachment_context, extract_image_context

logger = logging.getLogger(__name__)

REFINE_SYSTEM_PROMPT = (
    "You are an expert presentation designer and storytelling advisor. "
    "The user will share a presentation idea with optional images, "
    "PDF documents, and research findings.\n\n"
    "Your job is to produce a structured slide deck outline with:\n"
    "1. **Overview** — A clear one-paragraph summary of the presentation\n"
    "2. **Slide Sections** — For each slide, provide:\n"
    "   - **Title**: Clear, concise slide title\n"
    "   - **Content**: Key points or narrative for the slide (use bullet points)\n"
    "   - **Notes**: Speaker notes or talking points\n"
    "3. **Design Recommendations** — Visual style, color palette, imagery suggestions\n"
    "4. **Flow & Transitions** — How slides connect narratively\n\n"
    "When PDF content or image descriptions are provided, "
    "incorporate relevant details and visual style cues into your design.\n"
    "When research findings are provided, weave key data points into slide content.\n"
    "Be specific, visual, and presentation-ready. Use markdown formatting."
)


class SlidesAgent:
    """Agent that handles slide presentation operations."""

    def __init__(self, slides_service: InMemorySlidesService, research_service=None):
        self._service = slides_service
        self._research_service = research_service
        self._openai: AsyncAzureOpenAI | None = None

    def _get_openai(self) -> AsyncAzureOpenAI:
        if self._openai is None:
            from urllib.parse import urlparse

            from app.agents.config import _get_token_provider

            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.hostname}"
            token_provider = _get_token_provider()
            if token_provider:
                self._openai = AsyncAzureOpenAI(
                    azure_endpoint=base_url,
                    azure_ad_token_provider=token_provider,
                    api_version="2025-01-01-preview",
                )
            else:
                self._openai = AsyncAzureOpenAI(
                    azure_endpoint=base_url,
                    api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                    api_version="2025-01-01-preview",
                )
        return self._openai

    @property
    def tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_slides",
                    "description": "Create a new slide presentation with a title and description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The presentation title"},
                            "description": {
                                "type": "string",
                                "description": "The presentation description",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_slides_list",
                    "description": "List all slide presentations",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_slides",
                    "description": "Get a specific slide presentation by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slides_id": {
                                "type": "string",
                                "description": "The presentation ID",
                            },
                        },
                        "required": ["slides_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_slides",
                    "description": "Update a slide presentation's title and/or description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slides_id": {
                                "type": "string",
                                "description": "The presentation ID",
                            },
                            "title": {"type": "string", "description": "New title"},
                            "description": {"type": "string", "description": "New description"},
                        },
                        "required": ["slides_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_slides",
                    "description": "Delete a slide presentation by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slides_id": {
                                "type": "string",
                                "description": "The presentation ID",
                            },
                        },
                        "required": ["slides_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "refine_slides",
                    "description": (
                        "Refine a slide presentation into a structured deck outline using AI. "
                        "This runs in the background — tell the user it's starting and you'll "
                        "notify them when done."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slides_id": {
                                "type": "string",
                                "description": "The presentation ID to refine",
                            },
                        },
                        "required": ["slides_id"],
                    },
                },
            },
        ]

    async def _gather_research_context(self, slides_id: str | None) -> str:
        """Gather completed research linked to a presentation for use in refinement."""
        if not slides_id or not self._research_service:
            return ""
        try:
            items = await self._research_service.list_by_idea(slides_id)
            completed = [r for r in items if r.status == "completed" and r.result]
            if not completed:
                return ""
            parts = []
            for r in completed[:5]:
                entry = f"### Research: {r.title}\n{r.result[:2000]}"
                if r.citations:
                    refs = ", ".join(c.url for c in r.citations[:5])
                    entry += f"\nSources: {refs}"
                parts.append(entry)
            logger.info(
                "Including %d research item(s) in refinement for slides %s",
                len(completed),
                slides_id,
            )
            context = "\n\n---\nResearch findings (use these to inform your slide content):\n"
            return context + "\n\n".join(parts)
        except Exception:
            logger.warning("Failed to load research for slides %s", slides_id)
            return ""

    async def _extract_content(self, slides) -> tuple[str, str]:
        """Extract text from PDF attachments and AI descriptions from images."""
        import asyncio

        attachment_task = extract_attachment_context(getattr(slides, "attachments", None) or [])
        image_task = extract_image_context(getattr(slides, "images", None) or [])
        attachment_text, image_text = await asyncio.gather(attachment_task, image_task)
        return attachment_text, image_text

    async def refine(self, slides) -> str:
        """Refine a presentation using GPT-5.2 chat completions with PDF/image extraction."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        research_text = await self._gather_research_context(getattr(slides, "id", None))
        attachment_text, image_text = await self._extract_content(slides)

        slides_text = f"**Presentation: {slides.title}**\n\n{slides.description}"
        if research_text:
            slides_text += research_text
        if attachment_text:
            slides_text += attachment_text
        if image_text:
            slides_text += image_text

        content_parts: list[dict] = [{"type": "text", "text": slides_text}]

        if not image_text:
            upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
            for img_url in slides.images or []:
                filename = img_url.split("/")[-1]
                img_path = upload_dir / filename
                if img_path.exists():
                    data = base64.b64encode(img_path.read_bytes()).decode()
                    ext = filename.rsplit(".", 1)[-1].lower()
                    mime = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "gif": "image/gif",
                        "webp": "image/webp",
                    }.get(ext, "image/png")
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        }
                    )

        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                {"role": "user", "content": content_parts},
            ],
            max_completion_tokens=2000,
            temperature=0.7,
        )

        return response.choices[0].message.content or "Refinement failed."

    async def refine_stream(self, slides):
        """Stream-refine a presentation, yielding text chunks as they arrive."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        research_text = await self._gather_research_context(getattr(slides, "id", None))
        attachment_text, image_text = await self._extract_content(slides)

        slides_text = f"**Presentation: {slides.title}**\n\n{slides.description}"
        if research_text:
            slides_text += research_text
        if attachment_text:
            slides_text += attachment_text
        if image_text:
            slides_text += image_text

        content_parts: list[dict] = [{"type": "text", "text": slides_text}]

        if not image_text:
            upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
            for img_url in slides.images or []:
                filename = img_url.split("/")[-1]
                img_path = upload_dir / filename
                if img_path.exists():
                    data = base64.b64encode(img_path.read_bytes()).decode()
                    ext = filename.rsplit(".", 1)[-1].lower()
                    mime = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "gif": "image/gif",
                        "webp": "image/webp",
                    }.get(ext, "image/png")
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        }
                    )

        stream = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                {"role": "user", "content": content_parts},
            ],
            max_completion_tokens=2000,
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def handle_function_call(
        self, function_name: str, arguments: str, user_id: str = "default-user"
    ) -> str:
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        service = (
            self._service.with_user(user_id)
            if hasattr(self._service, "with_user")
            else self._service
        )

        if function_name == "create_slides":
            slides = await service.create(
                SlidesCreate(title=args["title"], description=args.get("description", ""))
            )
            if slides:
                return json.dumps(
                    {"success": True, "slides": {"id": slides.id, "title": slides.title}}
                )
            return json.dumps({"error": "Failed to create presentation"})

        elif function_name == "get_slides_list":
            items = await service.list()
            return json.dumps(
                {
                    "slides": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "status": s.status,
                            "description": s.description[:100],
                        }
                        for s in items
                    ]
                }
            )

        elif function_name == "get_slides":
            slides = await service.get_by_id(args["slides_id"])
            if slides:
                return json.dumps(
                    {
                        "slides": {
                            "id": slides.id,
                            "title": slides.title,
                            "description": slides.description,
                            "status": slides.status,
                            "refinedDraft": slides.refined_draft,
                        }
                    }
                )
            return json.dumps({"error": "Presentation not found"})

        elif function_name == "update_slides":
            update = SlidesUpdate(
                title=args.get("title"),
                description=args.get("description"),
            )
            slides = await service.update(args["slides_id"], update)
            if slides:
                return json.dumps(
                    {"success": True, "slides": {"id": slides.id, "title": slides.title}}
                )
            return json.dumps({"error": "Presentation not found"})

        elif function_name == "delete_slides":
            deleted = await service.delete(args["slides_id"])
            return json.dumps({"success": deleted})

        elif function_name == "refine_slides":
            slides = await service.get_by_id(args["slides_id"])
            if not slides:
                return json.dumps({"error": "Presentation not found"})
            try:
                draft = await self.refine(slides)
                await service.set_refined(slides.id, draft)
                return json.dumps(
                    {
                        "success": True,
                        "slides": {
                            "id": slides.id,
                            "title": slides.title,
                            "status": "refined",
                        },
                    }
                )
            except Exception:
                logger.exception("Failed to refine slides %s", slides.id)
                return json.dumps({"error": "Refinement failed"})

        return json.dumps({"error": f"Unknown function: {function_name}"})
