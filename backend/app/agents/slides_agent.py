"""Slides Agent — specialist agent for presentation CRUD and refinement."""

import json
import logging
import os

from openai import AsyncAzureOpenAI

from app.models.slides import SlidesCreate, SlidesUpdate
from app.services.memory_slides_service import InMemorySlidesService
from app.utils.extraction import extract_attachment_context

logger = logging.getLogger(__name__)

REFINE_SYSTEM_PROMPT = (
    "You are an expert presentation designer. "
    "The user will share a presentation idea with optional PowerPoint templates and research.\n\n"
    "Produce a structured output with exactly two sections:\n\n"
    "## Deck Config\n"
    "```yaml\n"
    "title: <presentation title>\n"
    "subtitle: <short subtitle>\n"
    "icon: <single emoji>\n"
    "theme: shadcn/ui\n"
    "appearance: dark\n"
    "palette: arctic\n"
    "```\n\n"
    "## Slides\n"
    "A numbered list of slides. Each slide has:\n"
    "- **Title**: Clear, concise slide title\n"
    "- **Content**: Exactly 2 sentences maximum — punchy and presentation-ready\n\n"
    "Example:\n"
    "1. **Introduction** — GitHub Copilot is an AI-powered coding assistant built into your editor. "
    "It helps you write code faster by suggesting completions, generating tests, and explaining code.\n\n"
    "Rules:\n"
    "- Keep each slide to 2 sentences MAX. Be concise and impactful.\n"
    "- Do NOT include speaker notes, design recommendations, or flow descriptions.\n"
    "- When PowerPoint templates or research are provided, incorporate relevant context.\n"
    "- Use markdown formatting."
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

    async def _extract_content(self, slides) -> str:
        """Extract text from PowerPoint attachments."""
        attachment_text = await extract_attachment_context(
            getattr(slides, "attachments", None) or []
        )
        return attachment_text

    @staticmethod
    def parse_deck_config(refined_draft: str) -> dict:
        """Extract Deck Config YAML block from refined draft."""
        import re
        import yaml

        match = re.search(r"```yaml\s*\n(.*?)```", refined_draft, re.DOTALL)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except Exception:
            return {}

    async def refine(self, slides) -> str:
        """Refine a presentation using GPT-5.2 chat completions."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        research_text = await self._gather_research_context(getattr(slides, "id", None))
        attachment_text = await self._extract_content(slides)

        slides_text = f"**Presentation: {slides.title}**\n\n{slides.description}"
        if research_text:
            slides_text += research_text
        if attachment_text:
            slides_text += attachment_text

        content_parts: list[dict] = [{"type": "text", "text": slides_text}]

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
        attachment_text = await self._extract_content(slides)

        slides_text = f"**Presentation: {slides.title}**\n\n{slides.description}"
        if research_text:
            slides_text += research_text
        if attachment_text:
            slides_text += attachment_text

        content_parts: list[dict] = [{"type": "text", "text": slides_text}]

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
