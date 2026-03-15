"""Spec Agent — specialist agent for spec CRUD and LLM-powered generation."""

import json
import logging
import os

from openai import AsyncAzureOpenAI

from app.models.spec import SpecCreate, SpecUpdate
from app.services.memory_spec_service import InMemorySpecService

logger = logging.getLogger(__name__)

FOUNDATION_SYSTEM_PROMPT = """You are an expert software architect. Given an idea description, produce a two-part spec in markdown.

Structure:

## Mockup Description

A concise ~200 word description of the frontend design covering: app name, layout structure, key UI components, primary user interactions, color scheme/visual identity, and demonstrated features. This is a visual design brief — describe what the user sees and does.

## OpenSpec Config

### Foundation

A single openspec-propose prompt instruction for the app's core architecture and foundation. This should be a clear, focused instruction that can be passed directly to `openspec-propose` as CLI input. It should cover: project scaffolding, tech stack choices, layout structure, navigation patterns, and core architectural patterns.

IMPORTANT:
- Mockup Description must be ~200 words max — concise and visual.
- The Foundation openspec-propose instruction should be clear, actionable, and directly usable as a single CLI prompt.
- Do NOT include features — those will be added separately.
- Focus on decisions, not explanations."""

FEATURES_SYSTEM_PROMPT = """You are an expert software architect. Given an idea description and its foundation spec (which contains a Mockup Description and a Foundation openspec-propose instruction), identify the MINIMUM set of features needed and produce them as markdown.

Structure your output EXACTLY as:

### Features

#### Feature: [Feature Name 1]
[An openspec-propose prompt instruction for this feature — a clear, focused instruction that can be passed directly to `openspec-propose` as CLI input]

#### Feature: [Feature Name 2]
[An openspec-propose prompt instruction for this feature]

[...repeat for each feature]

IMPORTANT:
- Keep feature count to an absolute minimum (typically 3-5 features).
- Each feature openspec-propose instruction should be self-contained and can run in parallel with other features.
- Each instruction should be clear, focused, and directly usable as a single CLI prompt.
- Do NOT include foundational concerns (those are in the Foundation instruction).
- Do NOT wrap in JSON or code fences — output raw markdown only.
- Do NOT include a Mockup Description or Foundation section — only output the ### Features section."""

ENHANCE_FEATURE_SYSTEM_PROMPT = """You are an expert software architect. Given an existing spec and a new feature description, produce two artifacts for adding this feature to the spec.

Output EXACTLY this structure (no extra text before or after):

## Mockup Addition

A 50-100 word paragraph describing the visual/interaction aspects of this feature — what the user sees and does. Write in present tense, matching the tone of the existing Mockup Description.

## Feature Entry

#### Feature: [Feature Name]
[An openspec-propose prompt instruction for this feature — a clear, focused instruction that can be passed directly to `openspec-propose` as CLI input. It should be self-contained and can run independently of other features.]

IMPORTANT:
- Read the existing spec carefully to ensure the feature is coherent with the foundation and existing features.
- The Feature Name should be concise and descriptive (2-4 words).
- The openspec-propose instruction should be actionable and directly usable as CLI input.
- Do NOT duplicate concerns already covered by the foundation or existing features.
- Do NOT wrap in code fences — output raw markdown only."""

OPTIMIZE_SYSTEM_PROMPT = """You are an expert technical writer. Optimize this development spec to be more concise, clear, and actionable.

Rules:
- PRESERVE the two-part format: "## Mockup Description" followed by "## OpenSpec Config" (with "### Foundation" and "### Features" subsections).
- Mockup Description should remain ~200 words max — concise and visual.
- Each openspec-propose instruction (Foundation and Feature blocks) should be clear, focused, and directly usable as CLI input.
- Remove redundancy and vague language.
- Use precise, actionable wording.
- Do NOT merge or remove sections.
- Do NOT change section headers.

Return only the improved markdown content."""


class SpecAgent:
    """Agent that handles spec operations including LLM-powered generation."""

    def __init__(self, spec_service: InMemorySpecService, brainstorm_service=None, research_service=None, dev_agent=None):
        self._service = spec_service
        self._brainstorm_service = brainstorm_service
        self._research_service = research_service
        self._dev_agent = dev_agent
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
            {
                "type": "function",
                "function": {
                    "name": "add_feature_to_spec",
                    "description": (
                        "Add a new feature to an existing foundation spec. "
                        "The feature description is enhanced using AI into a polished spec entry. "
                        "If the spec has a linked dev task in openspec mode, the feature is automatically "
                        "added to the dev task and the pipeline is triggered. "
                        "This runs in the background — tell the user it's starting."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "The foundation spec ID to add a feature to"},
                            "description": {"type": "string", "description": "Description of the feature to add (can be brief — AI will enhance it)"},
                        },
                        "required": ["spec_id", "description"],
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

        # 1. Generate foundation spec (Mockup Description + OpenSpec Config > Foundation)
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

        # 2. Generate features section (OpenSpec Config > Features)
        features_response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": FEATURES_SYSTEM_PROMPT},
                {"role": "user", "content": f"{user_content}\n\n---\nFoundation Spec:\n{foundation_content}"},
            ],
            max_completion_tokens=4000,
            temperature=0.5,
        )
        features_content = features_response.choices[0].message.content or ""

        # Combine into a single two-part spec
        combined_content = foundation_content.rstrip() + "\n\n" + features_content.strip()

        spec = await service.create(
            SpecCreate(
                title=title,
                content=combined_content,
                type="foundation",
                ideaId=idea_id,
            )
        )
        created_specs = [{"id": spec.id, "title": spec.title, "type": "foundation"}]

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

    async def enhance_feature(self, spec_content: str, feature_description: str) -> tuple[str, str, str]:
        """Enhance a raw feature description using GPT-5.2.

        Returns (feature_name, mockup_paragraph, openspec_propose_instruction).
        """
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": ENHANCE_FEATURE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Existing spec:\n\n{spec_content}\n\n---\n\n"
                        f"New feature to add: {feature_description}"
                    ),
                },
            ],
            max_completion_tokens=1500,
            temperature=0.5,
        )
        enhanced = response.choices[0].message.content or ""

        # Parse the mockup paragraph
        import re
        mockup_match = re.search(
            r'## Mockup Addition\s*\n(.*?)(?=\n## |\Z)', enhanced, re.DOTALL
        )
        mockup_paragraph = mockup_match.group(1).strip() if mockup_match else ""

        # Parse the feature entry (#### Feature: Name\n<instruction>)
        feature_match = re.search(
            r'#### Feature: (.+?)\n(.*?)(?=\n#### |\n### |\n## |\Z)',
            enhanced,
            re.DOTALL,
        )
        feature_name = feature_match.group(1).strip() if feature_match else feature_description[:50]
        propose_instruction = feature_match.group(2).strip() if feature_match else feature_description

        return feature_name, mockup_paragraph, propose_instruction

    async def add_feature_to_spec(
        self,
        spec_id: str,
        feature_description: str,
        user_id: str = "default-user",
    ) -> dict:
        """Add a feature to an existing spec: enhance → append → extend dev task → trigger pipeline.

        Returns a result dict with success status and details.
        """
        import re
        service = self._service.with_user(user_id) if hasattr(self._service, 'with_user') else self._service
        spec = await service.get_by_id(spec_id)
        if not spec:
            return {"error": "Spec not found"}
        if spec.type != "foundation":
            return {"error": "Features can only be added to foundation specs"}

        # 1. Enhance feature description with GPT-5.2
        feature_name, mockup_paragraph, propose_instruction = await self.enhance_feature(
            spec.content or "", feature_description
        )

        # 2. Append to spec content
        content = spec.content or ""

        # Append mockup paragraph to Mockup Description section
        if mockup_paragraph:
            mockup_end = re.search(r'(## Mockup Description\s*\n.*?)(?=\n## )', content, re.DOTALL)
            if mockup_end:
                insert_pos = mockup_end.end(1)
                content = content[:insert_pos] + f"\n\n{mockup_paragraph}" + content[insert_pos:]

        # Append feature entry to OpenSpec Config > Features section
        feature_entry = f"\n\n#### Feature: {feature_name}\n{propose_instruction}"
        # Try to append after the last #### Feature: block or after ### Features
        last_feature = None
        for m in re.finditer(
            r'#### Feature: .+?\n.*?(?=\n#### Feature:|\n### |\n## |\Z)',
            content,
            re.DOTALL,
        ):
            last_feature = m
        if last_feature:
            insert_pos = last_feature.end()
            content = content[:insert_pos] + feature_entry + content[insert_pos:]
        elif "### Features" in content:
            idx = content.index("### Features") + len("### Features")
            content = content[:idx] + feature_entry + content[idx:]
        else:
            content += f"\n\n### Features{feature_entry}"

        # Update spec
        from app.models.spec import SpecUpdate
        await service.update(spec_id, SpecUpdate(content=content))

        # 3. Detect linked dev task and extend it
        dev_task_extended = False
        pipeline_triggered = False
        if self._dev_agent and hasattr(spec, 'devTaskId') and spec.devTaskId:
            try:
                result = await self._dev_agent.append_feature_iteration(
                    task_id=spec.devTaskId,
                    feature_name=feature_name,
                    propose_instruction=propose_instruction,
                    spec_id=spec_id,
                    user_id=user_id,
                )
                dev_task_extended = result.get("extended", False)
                pipeline_triggered = result.get("pipeline_triggered", False)
            except Exception:
                logger.exception("Failed to extend dev task %s with new feature", spec.devTaskId)

        return {
            "success": True,
            "feature_name": feature_name,
            "spec_id": spec_id,
            "dev_task_extended": dev_task_extended,
            "pipeline_triggered": pipeline_triggered,
        }

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
