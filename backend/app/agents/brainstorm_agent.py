"""Brainstorm Agent — specialist agent for idea CRUD and refinement."""

import base64
import json
import logging
import os
from pathlib import Path

from openai import AsyncAzureOpenAI

from app.models.idea import IdeaCreate, IdeaUpdate
from app.services.memory_brainstorm_service import InMemoryBrainstormService

logger = logging.getLogger(__name__)

REFINE_SYSTEM_PROMPT = """You are an expert product development advisor. The user will share a raw idea with optional images.

Your job is to produce a structured, development-ready draft with:
1. **Summary** — A clear one-paragraph summary of the idea
2. **Key Features** — Bullet list of concrete features
3. **Gaps & Questions** — Things that are unclear or need decisions
4. **Technical Considerations** — Implementation notes, architecture hints
5. **Next Steps** — Actionable items to move forward

Be specific and constructive. Use markdown formatting."""


class BrainstormAgent:
    """Agent that handles brainstorm operations."""

    def __init__(self, brainstorm_service: InMemoryBrainstormService):
        self._service = brainstorm_service
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
                    "name": "create_idea",
                    "description": "Create a new brainstorm idea with a title and description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The idea title"},
                            "description": {"type": "string", "description": "The idea description"},
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_ideas",
                    "description": "List all brainstorm ideas",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_idea",
                    "description": "Get a specific brainstorm idea by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string", "description": "The idea ID"},
                        },
                        "required": ["idea_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_idea",
                    "description": "Update a brainstorm idea's title and/or description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string", "description": "The idea ID"},
                            "title": {"type": "string", "description": "New title"},
                            "description": {"type": "string", "description": "New description"},
                        },
                        "required": ["idea_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_idea",
                    "description": "Delete a brainstorm idea by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string", "description": "The idea ID"},
                        },
                        "required": ["idea_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "refine_idea",
                    "description": "Refine a brainstorm idea into a development-ready draft using AI. This runs in the background — tell the user it's starting and you'll notify them when done.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string", "description": "The idea ID to refine"},
                        },
                        "required": ["idea_id"],
                    },
                },
            },
        ]

    async def refine(self, idea) -> str:
        """Refine an idea using GPT-5.2 chat completions with optional vision."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        # Build user message content
        content_parts: list[dict] = [
            {
                "type": "text",
                "text": f"**Idea: {idea.title}**\n\n{idea.description}",
            }
        ]

        # Add images if available (base64 vision)
        upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
        for img_url in (idea.images or []):
            filename = img_url.split("/")[-1]
            img_path = upload_dir / filename
            if img_path.exists():
                data = base64.b64encode(img_path.read_bytes()).decode()
                ext = filename.rsplit(".", 1)[-1].lower()
                mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{data}"},
                })

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

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        service = self._service.with_user(user_id) if hasattr(self._service, 'with_user') else self._service

        if function_name == "create_idea":
            idea = await service.create(
                IdeaCreate(title=args["title"], description=args.get("description", ""))
            )
            if idea:
                return json.dumps({"success": True, "idea": {"id": idea.id, "title": idea.title}})
            return json.dumps({"error": "Failed to create idea"})

        elif function_name == "get_ideas":
            ideas = await service.list()
            return json.dumps({
                "ideas": [
                    {"id": i.id, "title": i.title, "status": i.status, "description": i.description[:100]}
                    for i in ideas
                ]
            })

        elif function_name == "get_idea":
            idea = await service.get_by_id(args["idea_id"])
            if idea:
                return json.dumps({
                    "idea": {
                        "id": idea.id, "title": idea.title,
                        "description": idea.description, "status": idea.status,
                        "refinedDraft": idea.refined_draft,
                    }
                })
            return json.dumps({"error": "Idea not found"})

        elif function_name == "update_idea":
            update = IdeaUpdate(
                title=args.get("title"),
                description=args.get("description"),
            )
            idea = await service.update(args["idea_id"], update)
            if idea:
                return json.dumps({"success": True, "idea": {"id": idea.id, "title": idea.title}})
            return json.dumps({"error": "Idea not found"})

        elif function_name == "delete_idea":
            deleted = await service.delete(args["idea_id"])
            return json.dumps({"success": deleted})

        elif function_name == "refine_idea":
            idea = await service.get_by_id(args["idea_id"])
            if not idea:
                return json.dumps({"error": "Idea not found"})
            try:
                draft = await self.refine(idea)
                await service.set_refined(idea.id, draft)
                return json.dumps({"success": True, "idea": {"id": idea.id, "title": idea.title, "status": "refined"}})
            except Exception:
                logger.exception("Failed to refine idea %s", idea.id)
                return json.dumps({"error": "Refinement failed"})

        return json.dumps({"error": f"Unknown function: {function_name}"})
