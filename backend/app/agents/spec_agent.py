"""Spec Agent — specialist agent for spec CRUD and LLM-powered generation."""

import json
import logging
import os

from openai import AsyncAzureOpenAI

from app.models.spec import SpecCreate, SpecUpdate
from app.services.memory_spec_service import InMemorySpecService

logger = logging.getLogger(__name__)

FOUNDATION_SYSTEM_PROMPT = """You are an expert software architect. Given an idea description, produce a concise foundation spec in markdown.

Structure:
## Overview
Brief summary of the application.

## Architecture
High-level architecture pattern and key decisions.

## Tech Stack
Languages, frameworks, databases, and infrastructure.

## Data Model
Core entities and their relationships.

## Core Patterns
Key design patterns, conventions, and constraints.

Keep it concise — no more than 500 words. Focus on decisions, not explanations."""

FEATURES_SYSTEM_PROMPT = """You are an expert software architect. Given an idea description and its foundation spec, identify the MINIMUM set of features needed.

For each feature, produce a concise spec in this markdown format:

## Overview
One sentence describing the feature.

## Requirements
- Bullet list of functional requirements (use SHALL).

## Acceptance Criteria
- Bullet list of testable criteria.

## Technical Notes
Brief implementation guidance.

IMPORTANT:
- Keep feature count to an absolute minimum (typically 3-5 features).
- Each feature should be focused on a single capability.
- Do NOT include foundational concerns (those are in the foundation spec).
- Respond with a JSON array of objects with "title" and "content" fields.

Example response:
[
  {"title": "User Authentication", "content": "## Overview\\n..."},
  {"title": "Data Dashboard", "content": "## Overview\\n..."}
]"""

OPTIMIZE_SYSTEM_PROMPT = """You are an expert technical writer. Optimize this development spec to be more concise, clear, and actionable.

Rules:
- Keep the same structure and sections.
- Remove redundancy and vague language.
- Use precise, actionable wording.
- Use SHALL for requirements.
- Keep it under 500 words.

Return only the improved markdown content."""


class SpecAgent:
    """Agent that handles spec operations including LLM-powered generation."""

    def __init__(self, spec_service: InMemorySpecService, brainstorm_service=None, research_service=None):
        self._service = spec_service
        self._brainstorm_service = brainstorm_service
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
                    "name": "create_spec",
                    "description": "Create a new development spec manually",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The spec title"},
                            "content": {"type": "string", "description": "The spec content in markdown"},
                            "type": {"type": "string", "enum": ["foundation", "feature"], "description": "Spec type"},
                            "parent_id": {"type": "string", "description": "Parent foundation spec ID (for feature specs)"},
                            "idea_id": {"type": "string", "description": "Source idea ID if linked"},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_specs",
                    "description": "List all development specs",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_spec",
                    "description": "Get a specific development spec by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "The spec ID"},
                        },
                        "required": ["spec_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_spec",
                    "description": "Update a development spec's title and/or content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "The spec ID"},
                            "title": {"type": "string", "description": "New title"},
                            "content": {"type": "string", "description": "New content"},
                        },
                        "required": ["spec_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_spec",
                    "description": "Delete a development spec by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "The spec ID"},
                        },
                        "required": ["spec_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_spec",
                    "description": "Generate a foundation spec and minimal feature specs from an idea using AI. This runs in the background — tell the user it's starting and you'll notify them when done. Provide either idea_id (to load from stored ideas) or title + description.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string", "description": "The idea ID to generate specs from"},
                            "title": {"type": "string", "description": "Idea title (if not using idea_id)"},
                            "description": {"type": "string", "description": "Idea description (if not using idea_id)"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_spec",
                    "description": "Optimize a spec using AI to make it more concise and clear. This runs in the background — tell the user it's starting and you'll notify them when done.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "The spec ID to optimize"},
                        },
                        "required": ["spec_id"],
                    },
                },
            },
        ]

    async def generate_from_idea(self, title: str, description: str, idea_id: str | None = None, user_id: str | None = None) -> list[dict]:
        """Generate foundation + feature specs from an idea. Returns list of created spec dicts."""
        service = self._service.with_user(user_id) if user_id else self._service
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")
        idea_text = f"**{title}**\n\n{description}"

        # Gather research linked to this idea
        research_context = ""
        if idea_id and self._research_service:
            try:
                research_items = await self._research_service.list_by_idea(idea_id)
                completed = [r for r in research_items if r.status == "completed" and r.result]
                if completed:
                    parts = []
                    for r in completed[:5]:  # max 5 research items
                        entry = f"### Research: {r.title}\n{r.result[:2000]}"
                        if r.citations:
                            refs = ", ".join(c.url for c in r.citations[:5])
                            entry += f"\nSources: {refs}"
                        parts.append(entry)
                    research_context = "\n\n---\nResearch findings:\n" + "\n\n".join(parts)
                    logger.info("Including %d research item(s) for idea %s in spec generation", len(completed), idea_id)
            except Exception:
                logger.warning("Failed to load research for idea %s", idea_id)

        user_content = idea_text + research_context

        # 1. Generate foundation spec
        foundation_response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": FOUNDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=2000,
            temperature=0.5,
        )
        foundation_content = foundation_response.choices[0].message.content or ""

        foundation = await service.create(
            SpecCreate(
                title=title,
                content=foundation_content,
                type="foundation",
                ideaId=idea_id,
            )
        )
        created_specs = [{"id": foundation.id, "title": foundation.title, "type": "foundation"}]

        # 2. Generate feature specs
        features_response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": FEATURES_SYSTEM_PROMPT},
                {"role": "user", "content": f"{user_content}\n\n---\nFoundation Spec:\n{foundation_content}"},
            ],
            max_completion_tokens=4000,
            temperature=0.5,
        )
        features_text = features_response.choices[0].message.content or "[]"

        # Parse feature specs JSON
        try:
            # Strip markdown code fences if present
            cleaned = features_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            features = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse features JSON, treating as single feature")
            features = [{"title": "Features", "content": features_text}]

        for feature in features:
            spec = await service.create(
                SpecCreate(
                    title=feature.get("title", "Untitled Feature"),
                    content=feature.get("content", ""),
                    type="feature",
                    parentId=foundation.id,
                    ideaId=idea_id,
                )
            )
            created_specs.append({"id": spec.id, "title": spec.title, "type": "feature"})

        return created_specs

    async def optimize(self, spec) -> str:
        """Optimize a spec's content using GPT-5.2."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": OPTIMIZE_SYSTEM_PROMPT},
                {"role": "user", "content": spec.content},
            ],
            max_completion_tokens=2000,
            temperature=0.3,
        )
        return response.choices[0].message.content or spec.content

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        service = self._service.with_user(user_id) if hasattr(self._service, 'with_user') else self._service

        if function_name == "create_spec":
            spec = await service.create(
                SpecCreate(
                    title=args["title"],
                    content=args.get("content", ""),
                    type=args.get("type", "foundation"),
                    parentId=args.get("parent_id"),
                    ideaId=args.get("idea_id"),
                )
            )
            if spec:
                return json.dumps({"success": True, "spec": {"id": spec.id, "title": spec.title, "type": spec.type}})
            return json.dumps({"error": "Failed to create spec"})

        elif function_name == "get_specs":
            specs = await service.list()
            return json.dumps({
                "specs": [
                    {"id": s.id, "title": s.title, "type": s.type, "status": s.status}
                    for s in specs
                ],
                "status_guidance": "Items with status 'draft' may still be generating if they were just created. "
                "Only offer to read content for specs that exist and have content.",
            })

        elif function_name == "get_spec":
            spec = await service.get_by_id(args["spec_id"])
            if spec:
                return json.dumps({
                    "spec": {
                        "id": spec.id, "title": spec.title,
                        "content": spec.content[:500] if spec.content else "",
                        "type": spec.type,
                        "status": spec.status,
                    },
                    "status_guidance": f"This spec is in '{spec.status}' status. "
                    + ("You can offer to read or optimize it." if spec.content else "It has no content yet."),
                })
            return json.dumps({"error": "Spec not found"})

        elif function_name == "update_spec":
            update = SpecUpdate(
                title=args.get("title"),
                content=args.get("content"),
            )
            spec = await service.update(args["spec_id"], update)
            if spec:
                return json.dumps({"success": True, "spec": {"id": spec.id, "title": spec.title}})
            return json.dumps({"error": "Spec not found"})

        elif function_name == "delete_spec":
            deleted = await service.delete(args["spec_id"])
            return json.dumps({"success": deleted})

        elif function_name == "generate_spec":
            idea_id = args.get("idea_id")
            title = args.get("title", "")
            description = args.get("description", "")

            brainstorm_svc = self._brainstorm_service
            if brainstorm_svc and hasattr(brainstorm_svc, 'with_user'):
                brainstorm_svc = brainstorm_svc.with_user(user_id)

            if idea_id and not title and brainstorm_svc:
                try:
                    idea = await brainstorm_svc.get_by_id(idea_id)
                    if idea:
                        title = idea.title
                        description = idea.description or ""
                    else:
                        return json.dumps({"error": f"Idea {idea_id} not found"})
                except Exception:
                    return json.dumps({"error": "Failed to look up idea"})

            if not title:
                return json.dumps({"error": "Please provide a title or idea_id"})

            try:
                created = await self.generate_from_idea(title, description, idea_id, user_id=user_id)
                return json.dumps({"success": True, "specs": created})
            except Exception:
                logger.exception("Failed to generate specs")
                return json.dumps({"error": "Spec generation failed"})

        elif function_name == "optimize_spec":
            spec = await service.get_by_id(args["spec_id"])
            if not spec:
                return json.dumps({"error": "Spec not found"})
            try:
                optimized = await self.optimize(spec)
                await service.set_optimized(spec.id, optimized)
                return json.dumps({"success": True, "spec": {"id": spec.id, "title": spec.title, "status": "optimized"}})
            except Exception:
                logger.exception("Failed to optimize spec %s", spec.id)
                return json.dumps({"error": "Optimization failed"})

        return json.dumps({"error": f"Unknown function: {function_name}"})
