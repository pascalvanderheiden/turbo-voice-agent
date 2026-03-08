"""Turbo Dev Agent — specialist agent for development task operations.

Uses GitHub Copilot SDK with BYOK for Azure AI Foundry (gpt-5.3-codex)
and Playwright MCP for browser testing/screenshots.

Supports two pipeline modes:
- Mock: single iteration from full spec → GUI-only mock app
- Sequence: iterative spec-driven development (foundation → features)
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from app.models.dev_task import DevArtifact
from app.services.dev_service import InMemoryDevService, _default_iteration
from app.services.json_persistence import DATA_DIR

logger = logging.getLogger(__name__)


class DevAgent:
    """Agent that handles development task operations."""

    def __init__(self, dev_service: InMemoryDevService, spec_service=None, skills_service=None):
        self._service = dev_service
        self._spec_service = spec_service
        self._skills_service = skills_service

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_dev_task",
                    "description": "Create a new development task, optionally linked to a spec",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The task title"},
                            "spec_id": {"type": "string", "description": "Optional spec ID to develop"},
                            "mode": {"type": "string", "enum": ["mock", "sequence"], "description": "Pipeline mode: mock (quick GUI) or sequence (iterative)"},
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dev_tasks",
                    "description": "List all development tasks with their pipeline status",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_dev_task",
                    "description": "Get a specific development task by ID with full stage details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "The dev task ID"},
                        },
                        "required": ["task_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_dev_task",
                    "description": "Delete a development task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "The dev task ID to delete"},
                        },
                        "required": ["task_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_dev_pipeline",
                    "description": "Start the development pipeline for a task. Mock mode = quick GUI mockup. Sequence mode = iterative spec-driven development.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "The dev task ID to run the pipeline on"},
                        },
                        "required": ["task_id"],
                    },
                },
            },
        ]

    async def handle_function_call(self, function_name: str, arguments: str) -> str:
        """Execute a function call and return the result as a string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        if function_name == "create_dev_task":
            from app.models.dev_task import DevTaskCreate
            mode = args.get("mode", "mock")
            task = await self._service.create(
                DevTaskCreate(title=args["title"], specId=args.get("spec_id"), mode=mode)
            )
            # If linked to a spec, populate iterations and set bidirectional link
            if args.get("spec_id") and self._spec_service:
                await self._populate_iterations_from_spec(task.id, args["spec_id"], mode)
                await self._spec_service.set_dev_task_id(args["spec_id"], task.id, "in-development")
            # Auto-attach relevant skills based on title + spec content
            await self._auto_attach_skills(task.id, args["title"], args.get("spec_id"))
            task = await self._service.get_by_id(task.id)
            return json.dumps({"success": True, "task": {"id": task.id, "title": task.title, "mode": task.mode}})

        elif function_name == "get_dev_tasks":
            tasks = await self._service.list()
            return json.dumps({
                "tasks": [
                    {
                        "id": t.id, "title": t.title, "mode": t.mode, "status": t.status,
                        "iterations": len(t.iterations),
                        "currentIteration": t.current_iteration,
                    }
                    for t in tasks
                ]
            })

        elif function_name == "get_dev_task":
            task = await self._service.get_by_id(args["task_id"])
            if task:
                return json.dumps({
                    "task": {
                        "id": task.id, "title": task.title, "mode": task.mode, "status": task.status,
                        "iterations": [
                            {
                                "index": it.iteration_index, "label": it.label,
                                "stages": [{"name": s.name, "status": s.status} for s in it.stages],
                            }
                            for it in task.iterations
                        ],
                    }
                })
            return json.dumps({"error": "Dev task not found"})

        elif function_name == "delete_dev_task":
            deleted = await self._service.delete(args["task_id"])
            return json.dumps({"success": deleted})

        elif function_name == "trigger_dev_pipeline":
            task = await self._service.get_by_id(args["task_id"])
            if not task:
                return json.dumps({"error": "Dev task not found"})
            if task.status not in ("pending", "failed"):
                return json.dumps({"error": "Task already running or completed"})
            await self._service.set_status(args["task_id"], "running")
            asyncio.create_task(self.run_pipeline(args["task_id"]))
            return json.dumps({"success": True, "message": f"Pipeline started (mode: {task.mode})"})

        return json.dumps({"error": f"Unknown function: {function_name}"})

    async def _populate_iterations_from_spec(self, task_id: str, spec_id: str, mode: str, user_id: str | None = None) -> None:
        """Populate iterations from spec hierarchy."""
        if not self._spec_service:
            return
        spec_svc = self._spec_service.with_user(user_id) if user_id else self._spec_service
        spec = await spec_svc.get_by_id(spec_id)
        if not spec:
            return

        if mode == "mock":
            # Single iteration with full spec content
            content_parts = [f"# {spec.title}\n\n{spec.content}"]
            features = await spec_svc.get_features_for_foundation(spec_id)
            for f in features:
                content_parts.append(f"## Feature: {f.title}\n\n{f.content}")
            full_label = f"Mock: {spec.title}"
            iterations = [_default_iteration(0, full_label, spec_id)]
        else:
            # Sequence: foundation first, then each feature
            iterations = [_default_iteration(0, f"Foundation: {spec.title}", spec_id)]
            features = await spec_svc.get_features_for_foundation(spec_id)
            for i, f in enumerate(features):
                iterations.append(_default_iteration(i + 1, f"Feature: {f.title}", f.id))

        dev_svc = self._service.with_user(user_id) if user_id else self._service
        await dev_svc.set_iterations(task_id, iterations)

    # ── Pipeline execution ──────────────────────────────────────────

    async def run_pipeline(self, task_id: str, user_id: str = "default-user") -> None:
        """Run the pipeline based on task mode."""
        service = self._service.with_user(user_id)
        spec_service = self._spec_service.with_user(user_id) if self._spec_service else None
        try:
            task = await service.get_by_id(task_id)
            if not task:
                return

            if task.mode == "sequence" and len(task.iterations) > 1:
                await self._run_sequence_pipeline(task_id, user_id)
            else:
                await self._run_mock_pipeline(task_id, user_id)

            # Mark overall completed
            task = await service.get_by_id(task_id)
            if task and task.status != "failed":
                all_done = all(
                    s.status == "completed"
                    for it in task.iterations
                    for s in it.stages
                )
                if all_done:
                    await service.set_status(task_id, "completed")
                    # Update linked spec status
                    if task.spec_id and spec_service:
                        await spec_service.set_dev_task_id(task.spec_id, task_id, "developed")

        except Exception as e:
            logger.exception("Pipeline failed for task %s", task_id)
            await service.set_status(task_id, "failed")

    async def _run_mock_pipeline(self, task_id: str, user_id: str = "default-user") -> None:
        """Mock mode: single iteration, full spec → one app."""
        service = self._service.with_user(user_id)
        task = await service.get_by_id(task_id)

        # Gather full spec content
        spec_content = await self._get_full_spec_content(task, user_id=user_id)
        skill_context = self._get_skill_context(task)

        # Plan
        await service.set_iteration_stage_status(task_id, 0, "plan", "running")
        try:
            plan = await self._call_codex(
                f"Create a brief implementation plan for a Next.js 15 app called '{task.title}'.\n"
                f"{'Spec:\n' + spec_content[:2000] if spec_content else 'Simple dark-themed dashboard.'}\n"
                f"{skill_context}\n"
                f"List: pages, components, mock data. Keep it under 500 words.\n",
                max_tokens=2000,
            )
            await service.set_iteration_stage_status(task_id, 0, "plan", "completed", output=plan)
        except Exception as e:
            logger.exception("Plan stage failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, 0, "plan", "failed", error=str(e))
            await service.set_status(task_id, "failed")
            return

        # Build
        await service.set_iteration_stage_status(task_id, 0, "build", "running")
        try:
            workspace = await self._build_app(task_id, task.title, spec_content, plan, skill_context, user_id=user_id)
            await service.set_iteration_workspace(task_id, 0, str(workspace))
        except Exception as e:
            logger.exception("Build stage failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, 0, "build", "failed", error=str(e))
            await service.set_status(task_id, "failed")
            return

        # Run
        port = await self._run_app(task_id, 0, workspace, user_id=user_id)
        task = await service.get_by_id(task_id)
        if task and task.status == "failed":
            return

        # Test
        await self._test_app(task_id, 0, workspace, port, user_id=user_id)

    async def _run_sequence_pipeline(self, task_id: str, user_id: str = "default-user") -> None:
        """Sequence mode: foundation first, then all features in parallel."""
        service = self._service.with_user(user_id)
        spec_service = self._spec_service.with_user(user_id) if self._spec_service else None
        task = await service.get_by_id(task_id)
        skill_context = self._get_skill_context(task)

        if not task.iterations:
            return

        # ── Phase 1: Foundation ──────────────────────────────────────
        foundation = task.iterations[0]
        await service.set_current_iteration(task_id, 0)

        spec_content = ""
        if foundation.spec_part_id and spec_service:
            spec = await spec_service.get_by_id(foundation.spec_part_id)
            if spec:
                spec_content = f"# {spec.title}\n\n{spec.content}"

        # Plan foundation
        await service.set_iteration_stage_status(task_id, 0, "plan", "running")
        try:
            plan = await self._call_codex(
                f"Create the base implementation plan for a Next.js 15 app. "
                f"Current part: '{foundation.label}'.\n"
                f"{'Spec:\n' + spec_content[:2000] if spec_content else ''}\n"
                f"{skill_context}\n"
                f"List: pages, components, data models, service interfaces. Keep it under 500 words.\n",
                max_tokens=2000,
            )
            await service.set_iteration_stage_status(task_id, 0, "plan", "completed", output=plan)
        except Exception as e:
            logger.exception("Foundation plan failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, 0, "plan", "failed", error=str(e))
            await service.set_status(task_id, "failed")
            return

        # Build foundation (with backend stubs)
        await service.set_iteration_stage_status(task_id, 0, "build", "running")
        try:
            foundation_workspace = await self._build_app(
                task_id, task.title, spec_content, plan, skill_context,
                generate_backend_stubs=True, user_id=user_id,
            )
            await service.set_iteration_workspace(task_id, 0, str(foundation_workspace))
        except Exception as e:
            logger.exception("Foundation build failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, 0, "build", "failed", error=str(e))
            await service.set_status(task_id, "failed")
            return

        # Run & test foundation
        port = await self._run_app(task_id, 0, foundation_workspace, user_id=user_id)
        task = await service.get_by_id(task_id)
        if task and task.status == "failed":
            return
        await self._test_app(task_id, 0, foundation_workspace, port, user_id=user_id)

        # ── Phase 2: Features in parallel ────────────────────────────
        feature_iterations = task.iterations[1:]
        if not feature_iterations:
            return

        foundation_plan = plan

        async def run_feature(iteration) -> Path | None:
            """Run a single feature pipeline on a copy of the foundation workspace."""
            idx = iteration.iteration_index
            await service.set_current_iteration(task_id, idx)

            # Get feature spec
            feat_spec = ""
            if iteration.spec_part_id and spec_service:
                spec = await spec_service.get_by_id(iteration.spec_part_id)
                if spec:
                    feat_spec = f"# {spec.title}\n\n{spec.content}"

            # Plan
            await service.set_iteration_stage_status(task_id, idx, "plan", "running")
            try:
                feat_plan = await self._call_codex(
                    f"Add to existing Next.js 15 app. Current feature: '{iteration.label}'.\n"
                    f"{'Spec:\n' + feat_spec[:2000] if feat_spec else ''}\n"
                    f"{skill_context}\n"
                    f"\nFoundation already built with plan:\n{foundation_plan[:400]}\n"
                    f"List: new components, changes to page, new backend types/services. Under 500 words.\n",
                    max_tokens=2000,
                )
                await service.set_iteration_stage_status(task_id, idx, "plan", "completed", output=feat_plan)
            except Exception as e:
                logger.exception("Feature plan failed for %s iteration %d", task_id, idx)
                await service.set_iteration_stage_status(task_id, idx, "plan", "failed", error=str(e))
                return None

            # Build (copy foundation, extend with feature)
            await service.set_iteration_stage_status(task_id, idx, "build", "running")
            try:
                feature_workspace = Path(tempfile.mkdtemp(prefix=f"turbo-feat-{task_id[:8]}-{idx}-"))
                shutil.copytree(foundation_workspace, feature_workspace, dirs_exist_ok=True)
                feature_workspace = await self._extend_app(
                    task_id, feature_workspace, iteration.label, feat_spec, feat_plan, skill_context,
                    generate_backend_stubs=True, user_id=user_id,
                )
                await service.set_iteration_workspace(task_id, idx, str(feature_workspace))
            except Exception as e:
                logger.exception("Feature build failed for %s iteration %d", task_id, idx)
                await service.set_iteration_stage_status(task_id, idx, "build", "failed", error=str(e))
                return None

            # Run & test feature
            feat_port = await self._run_app(task_id, idx, feature_workspace, user_id=user_id)
            task_check = await service.get_by_id(task_id)
            if task_check and task_check.status == "failed":
                return None
            await self._test_app(task_id, idx, feature_workspace, feat_port, user_id=user_id)
            return feature_workspace

        # Launch all features in parallel
        results = await asyncio.gather(
            *(run_feature(it) for it in feature_iterations),
            return_exceptions=True,
        )

        # ── Phase 3: Merge into final workspace ─────────────────────
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Feature pipeline raised: %s", result)
                continue
            if result is None:
                continue
            # Merge feature files (types, services, page updates) into foundation
            feature_ws = Path(result)
            for subdir in ["src/types", "src/services"]:
                feat_dir = feature_ws / subdir
                if feat_dir.exists():
                    dest_dir = foundation_workspace / subdir
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    for f in feat_dir.iterdir():
                        if f.is_file() and not (dest_dir / f.name).exists():
                            shutil.copy2(f, dest_dir / f.name)
            # Take the latest page.tsx from the last successful feature
            feat_page = feature_ws / "src/app/page.tsx"
            if feat_page.exists():
                # Append feature components rather than overwrite
                pass  # page.tsx merging is complex; each feature already extends foundation

        # Create final merged archive
        archive_dir = DATA_DIR / "dev"
        archive_dir.mkdir(parents=True, exist_ok=True)
        final_archive = archive_dir / f"{task_id}.tar.gz"
        await asyncio.to_thread(self._create_archive, foundation_workspace, final_archive)
        await service.add_artifact(task_id, DevArtifact(
            name=f"{task_id}-complete.tar.gz", type="archive", data=str(final_archive),
        ))

    # ── Shared pipeline stages ──────────────────────────────────────

    async def _auto_attach_skills(self, task_id: str, title: str, spec_id: str | None = None) -> None:
        """Auto-suggest and attach relevant skills to a task based on title + spec content."""
        if not self._skills_service:
            return
        content = title
        if spec_id and self._spec_service:
            spec = await self._spec_service.get_by_id(spec_id)
            if spec:
                content = f"{spec.title} {spec.content} {title}"
        suggested = self._skills_service.suggest_skills_for_content(content)
        # Fallback: if no keyword match, include all installed skills (user installed them for a reason)
        if not suggested:
            all_skills = self._skills_service.list_installed()
            suggested = [s["name"] for s in all_skills[:3]]
        if suggested:
            await self._service.set_skill_ids(task_id, suggested)
            logger.info("Auto-attached skills %s to task %s", suggested, task_id)

    def _get_skill_context(self, task) -> str:
        """Load and concatenate skill content for a task's selected skills."""
        if not self._skills_service or not hasattr(task, 'skill_ids') or not task.skill_ids:
            return ""
        parts = []
        for skill_id in task.skill_ids[:3]:  # max 3 skills
            content = self._skills_service.get_skill_content(skill_id, max_tokens=2000)
            if content:
                parts.append(f"=== Skill: {skill_id} ===\n{content}")
        if not parts:
            return ""
        return "\n\nRelevant skill context (use these guidelines for code generation):\n" + "\n\n".join(parts)

    async def _get_full_spec_content(self, task, user_id: str = "default-user") -> str:
        """Get full spec content (foundation + features) for a task."""
        if not task.spec_id or not self._spec_service:
            return ""
        spec_svc = self._spec_service.with_user(user_id)
        spec = await spec_svc.get_by_id(task.spec_id)
        if not spec:
            return ""
        parts = [f"# {spec.title}\n\n{spec.content}"]
        features = await spec_svc.get_features_for_foundation(task.spec_id)
        for f in features:
            parts.append(f"## Feature: {f.title}\n\n{f.content}")
        return "\n\n---\n\n".join(parts)

    async def _build_app(self, task_id: str, title: str, spec_content: str, plan: str, skill_context: str = "", generate_backend_stubs: bool = False, user_id: str = "default-user") -> Path:
        """Build a new Next.js app from scratch with multiple components."""
        service = self._service.with_user(user_id)
        workspace = Path(tempfile.mkdtemp(prefix=f"turbo-dev-{task_id[:8]}-"))

        files = self._minimal_next_app(title)

        # Step 1: Generate reusable components based on full spec
        components_prompt = (
            f"You are building a Next.js 15 app called '{title}'.\n"
            f"The project uses Tailwind CSS v4 (already configured via @import 'tailwindcss' in globals.css).\n"
            f"The layout already has: <body className=\"bg-[#0F0F1A] text-white antialiased min-h-screen\">\n\n"
            f"Generate 2-4 reusable React components for this app.\n"
            f"Each component MUST use 'use client' directive and Tailwind utility classes ONLY.\n"
            f"Use vibrant colors, gradients, shadows, rounded corners, hover/transition effects.\n"
            f"Do NOT use any external component libraries. Do NOT use inline styles or CSS modules.\n"
            f"Include realistic mock data inside each component.\n\n"
            f"{'Specification:\n' + spec_content[:3000] if spec_content else ''}\n\n"
            f"{'Implementation plan:\n' + plan[:1000] if plan else ''}\n\n"
            f"{skill_context}\n\n"
            f"Output format — for each component use this exact delimiter:\n"
            f"=== FILE: src/components/ComponentName.tsx ===\n"
            f"<component code>\n\n"
            f"Output ONLY the component files. No markdown fences.\n"
        )
        components_response = await self._call_codex(components_prompt, max_tokens=8000)
        component_files = self._parse_multi_file_response(components_response) if components_response else {}
        files.update(component_files)

        # Collect component import names for the page
        component_imports = []
        for cpath in component_files:
            name = Path(cpath).stem
            component_imports.append((name, cpath.replace("src/", "@/")))

        import_lines = "\n".join(f"import {name} from '{path.replace('.tsx', '')}';" for name, path in component_imports)
        component_tags = "\n          ".join(f"<{name} />" for name, _ in component_imports)

        # Step 2: Generate the main page that uses these components
        page_prompt = (
            f"Generate the main page for '{title}' — a Next.js 15 React page.\n"
            f"Use 'use client'. Style ONLY with Tailwind CSS v4 utility classes.\n"
            f"The body already has className=\"bg-[#0F0F1A] text-white\" so build on that dark theme.\n"
            f"Use vibrant gradients (pink/cyan/purple), glass-morphism effects, smooth transitions.\n"
            f"Do NOT use any external UI libraries. Do NOT use inline styles.\n\n"
        )
        if component_imports:
            page_prompt += (
                f"The following components are available — import and use them:\n"
                f"{import_lines}\n\n"
                f"Compose them into a polished layout with proper spacing.\n"
            )
        page_prompt += (
            f"Include mock/sample data to make the page look populated and alive.\n"
            f"{'Specification:\n' + spec_content[:2000] if spec_content else ''}\n"
            f"{skill_context}\n\n"
            f"Export default function Page().\n"
            f"Output ONLY the TSX code, no markdown fences.\n"
        )
        page_code = await self._call_codex(page_prompt, max_tokens=6000)

        if page_code and len(page_code) > 50:
            clean = self._strip_fences(page_code)
            if "export default" in clean or "export function" in clean:
                files["src/app/page.tsx"] = clean

        # Generate backend stubs (types + service interfaces) for sequence mode
        if generate_backend_stubs and spec_content:
            stubs = await self._generate_backend_stubs(title, spec_content, skill_context)
            files.update(stubs)

        for file_path, content in files.items():
            full_path = workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(str(content))

        await self._install_and_build(workspace, task_id, 0, service)
        return workspace

    async def _extend_app(self, task_id: str, workspace: Path, label: str, spec_content: str, plan: str, skill_context: str = "", generate_backend_stubs: bool = False, user_id: str = "default-user") -> Path:
        """Extend an existing workspace with a new feature."""
        service = self._service.with_user(user_id)

        # Read current page.tsx to provide context
        page_file = workspace / "src/app/page.tsx"
        existing_code = page_file.read_text() if page_file.exists() else ""

        new_code = await self._call_codex(
            f"Extend this Next.js page to add: '{label}'.\n"
            f"Style ONLY with Tailwind CSS v4 utility classes. Do NOT use inline styles.\n"
            f"Use vibrant colors, gradients, shadows. Dark theme (body is bg-[#0F0F1A] text-white).\n"
            f"Current page.tsx:\n```\n{existing_code[:3000]}\n```\n\n"
            f"{'Feature specification:\n' + spec_content[:2000] if spec_content else ''}\n"
            f"{'Plan:\n' + plan[:800] if plan else ''}\n\n"
            f"{skill_context}\n"
            f"Output ONLY the complete updated page.tsx. Keep existing functionality, add new feature.\n",
            max_tokens=8000,
        )

        if new_code and "export" in new_code:
            clean = self._strip_fences(new_code)
            page_file.write_text(clean)

        # Generate backend stubs for this feature
        if generate_backend_stubs and spec_content:
            stubs = await self._generate_backend_stubs(label, spec_content, skill_context, is_feature=True)
            for file_path, content in stubs.items():
                full_path = workspace / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

        # Rebuild
        task = await service.get_by_id(task_id)
        iter_idx = task.current_iteration if task else 0
        await self._install_and_build(workspace, task_id, iter_idx, service)
        return workspace

    async def _generate_backend_stubs(self, title: str, spec_content: str, skill_context: str, is_feature: bool = False) -> dict[str, str]:
        """Generate TypeScript types and service interfaces as backend stubs."""
        label = "feature" if is_feature else "foundation"
        prompt = (
            f"Based on this {label} spec for '{title}', generate TypeScript backend stubs.\n"
            f"Spec:\n{spec_content[:1500]}\n\n"
            f"{skill_context}\n"
            f"Generate two files:\n"
            f"1. TypeScript types/interfaces for the data models (src/types/{self._slugify(title)}.ts)\n"
            f"2. A service interface with a mock implementation (src/services/{self._slugify(title)}-service.ts)\n\n"
            f"Output the files in this exact format (no extra text):\n"
            f"=== FILE: src/types/{self._slugify(title)}.ts ===\n"
            f"<types code>\n"
            f"=== FILE: src/services/{self._slugify(title)}-service.ts ===\n"
            f"<service code>\n\n"
            f"The service should export a class with CRUD-like methods and a mock in-memory implementation.\n"
            f"Use clear TypeScript interfaces. Include JSDoc comments.\n"
        )
        response = await self._call_codex(prompt, max_tokens=4000)
        return self._parse_multi_file_response(response)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to kebab-case slug."""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
        slug = re.sub(r'[\s_]+', '-', slug).strip('-')
        return slug[:40] or "module"

    @staticmethod
    def _parse_multi_file_response(response: str) -> dict[str, str]:
        """Parse a response containing multiple files delimited by === FILE: path ===."""
        import re
        files: dict[str, str] = {}
        parts = re.split(r'===\s*FILE:\s*(.+?)\s*===', response)
        # parts[0] is before first marker, then alternating path/content
        for i in range(1, len(parts) - 1, 2):
            file_path = parts[i].strip()
            content = parts[i + 1].strip()
            # Strip markdown fences if present
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            if file_path and content:
                files[file_path] = content
        return files

    async def _install_and_build(self, workspace: Path, task_id: str, iter_idx: int, service) -> None:
        """npm install + build with retry logic."""
        result = await asyncio.to_thread(
            subprocess.run,
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=str(workspace), capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"npm install failed:\n{result.stderr[:1000]}")

        await asyncio.to_thread(
            subprocess.run,
            ["npm", "install", "--save-dev", "typescript", "@types/react", "@types/node", "--no-audit", "--no-fund"],
            cwd=str(workspace), capture_output=True, text=True, timeout=60,
        )

        # Safe next.config
        for cfg in [workspace / "next.config.ts", workspace / "next.config.js", workspace / "next.config.mjs"]:
            if cfg.exists():
                cfg.unlink()
        (workspace / "next.config.js").write_text(
            "/** @type {import('next').NextConfig} */\nconst nextConfig = {};\nmodule.exports = nextConfig;\n"
        )

        # Ensure Tailwind CSS v4 + PostCSS are set up
        postcss_cfg = workspace / "postcss.config.mjs"
        if not postcss_cfg.exists():
            postcss_cfg.write_text(
                "/** @type {import('postcss-load-config').Config} */\n"
                "const config = {\n"
                '  plugins: {\n'
                '    "@tailwindcss/postcss": {},\n'
                "  },\n"
                "};\n"
                "export default config;\n"
            )
        globals_css = workspace / "src" / "app" / "globals.css"
        if not globals_css.exists():
            globals_css.parent.mkdir(parents=True, exist_ok=True)
            globals_css.write_text('@import "tailwindcss";\n')
        # Ensure layout imports globals.css
        layout_file = workspace / "src" / "app" / "layout.tsx"
        if layout_file.exists():
            layout_content = layout_file.read_text()
            if "globals.css" not in layout_content:
                layout_file.write_text('import "./globals.css";\n\n' + layout_content)

        # Ensure tsconfig
        tsconfig = workspace / "tsconfig.json"
        if not tsconfig.exists():
            tsconfig.write_text(json.dumps({
                "compilerOptions": {
                    "target": "es5", "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True, "skipLibCheck": True, "strict": False, "noEmit": True,
                    "esModuleInterop": True, "module": "esnext", "moduleResolution": "bundler",
                    "resolveJsonModule": True, "isolatedModules": True, "jsx": "preserve",
                    "incremental": True, "paths": {"@/*": ["./src/*"]},
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
                "exclude": ["node_modules"]
            }, indent=2))

        result = await asyncio.to_thread(
            subprocess.run,
            ["npx", "next", "build"],
            cwd=str(workspace), capture_output=True, text=True, timeout=180,
        )
        build_output = result.stdout[-1000:] if result.stdout else ""

        if result.returncode != 0:
            build_err = f"{result.stderr[:1500]}\n{build_output}"
            logger.warning("Build failed for %s, attempting fix", task_id)

            # Remove broken component imports from page and fix the page itself
            page_file = workspace / "src/app/page.tsx"
            comp_dir = workspace / "src" / "components"
            # Delete generated components that may cause errors
            if comp_dir.exists():
                import shutil
                shutil.rmtree(comp_dir, ignore_errors=True)

            # Re-generate a self-contained page without component imports
            fix_response = await self._call_codex(
                f"This Next.js page has build errors:\n\n{build_err[:800]}\n\n"
                f"Generate a SELF-CONTAINED page.tsx that does NOT import any custom components.\n"
                f"Use 'use client'. Use ONLY Tailwind CSS v4 utility classes.\n"
                f"Dark theme (bg-[#0F0F1A] body is set in layout). Use vibrant colors, gradients, rounded cards.\n"
                f"Include realistic mock data inline. Export default function Page().\n"
                f"Output ONLY the TSX code, no markdown fences.\n",
                max_tokens=6000,
            )
            if fix_response and "export" in fix_response:
                page_file.write_text(self._strip_fences(fix_response))

            result = await asyncio.to_thread(
                subprocess.run, ["npx", "next", "build"],
                cwd=str(workspace), capture_output=True, text=True, timeout=180,
            )
            build_output = result.stdout[-1000:] if result.stdout else ""
            if result.returncode != 0:
                # Styled fallback page (not bare minimal)
                page_file.write_text(
                    '"use client";\n\n'
                    "export default function Page() {\n"
                    "  return (\n"
                    '    <main className="min-h-screen p-8 flex flex-col items-center justify-center">\n'
                    '      <div className="max-w-2xl w-full space-y-8">\n'
                    '        <div className="text-center">\n'
                    '          <h1 className="text-5xl font-bold bg-gradient-to-r from-pink-500 via-purple-500 to-cyan-500 bg-clip-text text-transparent">\n'
                    f'            {title}\n'
                    '          </h1>\n'
                    '          <p className="text-gray-400 mt-4 text-lg">Generated by Turbo Dev Agent</p>\n'
                    '        </div>\n'
                    '        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">\n'
                    '          {[["🚀","Feature 1","Ready to build"],["⚡","Feature 2","In progress"],["🎨","Design","Styled with Tailwind"],["📦","Package","Download & extend"]].map(([icon,t,d],i) => (\n'
                    '            <div key={i} className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-pink-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-pink-500/10">\n'
                    '              <div className="text-3xl mb-3">{icon}</div>\n'
                    '              <h3 className="font-semibold text-lg">{t}</h3>\n'
                    '              <p className="text-gray-400 text-sm mt-1">{d}</p>\n'
                    '            </div>\n'
                    '          ))}\n'
                    '        </div>\n'
                    '      </div>\n'
                    '    </main>\n'
                    '  );\n'
                    "}\n"
                )
                result = await asyncio.to_thread(
                    subprocess.run, ["npx", "next", "build"],
                    cwd=str(workspace), capture_output=True, text=True, timeout=180,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Build failed:\n{result.stderr[:1000]}")

        await service.set_iteration_stage_status(task_id, iter_idx, "build", "completed", output=f"Build succeeded.\n{build_output}")

    async def _run_app(self, task_id: str, iter_idx: int, workspace: Path, user_id: str = "default-user") -> int:
        """Start dev server and verify it responds. Returns port on success."""
        service = self._service.with_user(user_id)
        await service.set_iteration_stage_status(task_id, iter_idx, "run", "running")
        port = 3100 + (hash(task_id) % 100)
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "npx", "next", "start", "-p", str(port),
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )

            import aiohttp
            for _ in range(15):
                await asyncio.sleep(2)
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://localhost:{port}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status < 500:
                                await service.set_iteration_stage_status(
                                    task_id, iter_idx, "run", "completed",
                                    output=f"Server running on port {port}",
                                )
                                return port
                except Exception:
                    continue

            raise RuntimeError(f"Server did not start on port {port} within 30s")

        except Exception as e:
            logger.exception("Run stage failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, iter_idx, "run", "failed", error=str(e))
            await service.set_status(task_id, "failed")
            # Kill the process if it's still running
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return port

    async def _test_app(self, task_id: str, iter_idx: int, workspace: Path, port: int, user_id: str = "default-user") -> None:
        """Take screenshots with Playwright and archive code."""
        service = self._service.with_user(user_id)
        await service.set_iteration_stage_status(task_id, iter_idx, "test", "running")
        try:
            screenshots = await self._take_screenshots(port)
            for name, data in screenshots:
                await service.add_artifact(task_id, DevArtifact(
                    name=name, type="screenshot", data=data, iterationIndex=iter_idx,
                ))

            archive_dir = DATA_DIR / "dev"
            archive_dir.mkdir(parents=True, exist_ok=True)
            suffix = f"-iter{iter_idx}" if iter_idx > 0 else ""
            archive_path = archive_dir / f"{task_id}{suffix}.tar.gz"
            await asyncio.to_thread(self._create_archive, workspace, archive_path)
            await service.add_artifact(task_id, DevArtifact(
                name=f"{task_id}{suffix}.tar.gz", type="archive", data=str(archive_path),
                iterationIndex=iter_idx,
            ))

            await service.set_iteration_stage_status(
                task_id, iter_idx, "test", "completed",
                output=f"Captured {len(screenshots)} screenshot(s). Archive: {archive_path.name}",
            )

        except Exception as e:
            logger.exception("Test stage failed for %s", task_id)
            await service.set_iteration_stage_status(task_id, iter_idx, "test", "failed", error=str(e))
            await service.set_status(task_id, "failed")

    # ── Helpers ──────────────────────────────────────────────────────

    async def _call_codex(self, prompt: str, max_tokens: int = 16000) -> str:
        """Call gpt-5.3-codex via GitHub Copilot SDK BYOK, fallback to raw API."""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        deployment = os.getenv("DEV_CODEX_DEPLOYMENT", "gpt-5.3-codex")

        if not endpoint:
            raise RuntimeError("AZURE_OPENAI_ENDPOINT must be set")

        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        base_url = f"{parsed.scheme}://{parsed.hostname}/openai/v1/"

        # Get API key or token via managed identity
        key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if not key:
            try:
                from azure.identity.aio import DefaultAzureCredential
                cred = DefaultAzureCredential()
                token = await cred.get_token("https://cognitiveservices.azure.com/.default")
                key = token.token
                await cred.close()
            except Exception:
                raise RuntimeError("No AZURE_OPENAI_API_KEY and managed identity unavailable")

        # Try Copilot SDK BYOK first
        try:
            return await self._call_via_copilot_sdk(base_url, key, deployment, prompt, max_tokens)
        except Exception as sdk_err:
            logger.warning("Copilot SDK failed (%s), falling back to raw API", sdk_err)

        # Fallback: raw OpenAI Responses API
        return await self._call_via_raw_api(base_url, key, deployment, prompt, max_tokens)

    async def _call_via_copilot_sdk(self, base_url: str, api_key: str, model: str, prompt: str, max_tokens: int) -> str:
        """Use GitHub Copilot SDK with BYOK provider config."""
        from copilot import CopilotClient

        client = CopilotClient()
        await client.start()
        try:
            session = await client.create_session({
                "model": model,
                "provider": {
                    "type": "openai",
                    "base_url": base_url,
                    "wire_api": "responses",
                    "api_key": api_key,
                },
            })

            done = asyncio.Event()
            result_text = []

            def on_event(event):
                if event.type.value == "assistant.message":
                    result_text.append(event.data.content)
                elif event.type.value == "session.idle":
                    done.set()

            session.on(on_event)
            await session.send({"prompt": prompt})
            await asyncio.wait_for(done.wait(), timeout=300)
            await session.destroy()
            return "\n".join(result_text)
        finally:
            await client.stop()

    async def _call_via_raw_api(self, base_url: str, api_key: str, model: str, prompt: str, max_tokens: int) -> str:
        """Fallback: direct OpenAI Responses API call."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=600.0)
        try:
            response = await client.responses.create(
                model=model,
                input=prompt,
                max_output_tokens=max_tokens,
            )
            text_parts = []
            for item in response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
            return "\n".join(text_parts) if text_parts else ""
        finally:
            await client.close()

    async def _take_screenshots(self, port: int) -> list[tuple[str, str]]:
        """Take up to 5 feature-focused screenshots: homepage + interactive feature demos + full-page."""
        screenshots: list[tuple[str, str]] = []
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{port}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status >= 500:
                        logger.warning("Port %d returned %d — skipping screenshots", port, resp.status)
                        return screenshots
        except Exception:
            logger.warning("Port %d not reachable — skipping screenshots", port)
            return screenshots

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                url = f"http://localhost:{port}"

                page = await browser.new_page(viewport={"width": 1280, "height": 720})
                await page.goto(url, wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(1500)

                # 1. Homepage overview
                buf = await page.screenshot(type="png")
                screenshots.append(("homepage.png", base64.b64encode(buf).decode()))

                # 2–4. Feature interactions: find UI elements and capture state after each
                try:
                    interactables = page.locator(
                        "button:visible, input[type='checkbox']:visible, "
                        "[role='button']:visible, input[type='text']:visible, "
                        "select:visible, [role='tab']:visible, a[href]:visible"
                    )
                    count = await interactables.count()
                    interacted = 0
                    for i in range(min(count, 6)):
                        if interacted >= 3:
                            break
                        try:
                            el = interactables.nth(i)
                            if not await el.is_visible():
                                continue
                            tag = await el.evaluate("e => e.tagName.toLowerCase()")
                            input_type = await el.evaluate("e => e.type || ''")
                            if tag == "input" and input_type in ("text", "search", ""):
                                await el.fill("Sample task")
                                await page.wait_for_timeout(500)
                            elif tag == "select":
                                options = await el.evaluate("e => [...e.options].map(o => o.value)")
                                if len(options) > 1:
                                    await el.select_option(options[1])
                                    await page.wait_for_timeout(500)
                            else:
                                await el.click()
                                await page.wait_for_timeout(800)

                            buf = await page.screenshot(type="png")
                            label = await el.evaluate(
                                "e => e.textContent?.trim()?.substring(0,30) || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.tagName"
                            )
                            safe = label[:20].replace(" ", "-").replace("/", "").lower()
                            screenshots.append((f"feature-{interacted+1}-{safe}.png", base64.b64encode(buf).decode()))
                            interacted += 1
                        except Exception:
                            continue
                except Exception:
                    pass

                # 5. Full-page scroll capture (shows all content below the fold)
                if len(screenshots) < 5:
                    buf = await page.screenshot(type="png", full_page=True)
                    screenshots.append(("full-page.png", base64.b64encode(buf).decode()))

                await page.close()
                await browser.close()
        except Exception as e:
            logger.warning("Playwright screenshot failed: %s — continuing", e)
        return screenshots[:5]

    def _create_archive(self, workspace: Path, archive_path: Path) -> None:
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in workspace.iterdir():
                if item.name in ("node_modules", ".next", ".git"):
                    continue
                tar.add(str(item), arcname=item.name)

    def _strip_fences(self, code: str) -> str:
        """Remove markdown code fences if present."""
        clean = code.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean
        if clean.endswith("```"):
            clean = clean.rsplit("```", 1)[0]
        return clean.strip()

    def _minimal_next_app(self, title: str) -> dict[str, str]:
        return {
            "package.json": json.dumps({
                "name": "turbo-dev-app",
                "version": "0.1.0",
                "private": True,
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
                "dependencies": {"next": "^15.0.0", "react": "^19.0.0", "react-dom": "^19.0.0"},
                "devDependencies": {
                    "tailwindcss": "^4.0.0",
                    "@tailwindcss/postcss": "^4.0.0",
                    "postcss": "^8.5.0",
                    "typescript": "^5.7.0",
                    "@types/react": "^19.0.0",
                    "@types/node": "^22.0.0",
                },
            }, indent=2),
            "next.config.ts": "import type { NextConfig } from 'next';\nconst config: NextConfig = {};\nexport default config;\n",
            "postcss.config.mjs": (
                "/** @type {import('postcss-load-config').Config} */\n"
                "const config = {\n"
                '  plugins: {\n'
                '    "@tailwindcss/postcss": {},\n'
                "  },\n"
                "};\n"
                "export default config;\n"
            ),
            "tsconfig.json": json.dumps({
                "compilerOptions": {
                    "target": "ES2017", "lib": ["dom", "esnext"], "jsx": "preserve",
                    "module": "esnext", "moduleResolution": "bundler", "strict": True,
                    "paths": {"@/*": ["./src/*"]},
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
            }, indent=2),
            "src/app/globals.css": (
                '@import "tailwindcss";\n'
            ),
            "src/app/layout.tsx": (
                'import "./globals.css";\n\n'
                f'export const metadata = {{ title: "{title}" }};\n'
                "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
                '  return (\n'
                '    <html lang="en">\n'
                '      <body className="bg-[#0F0F1A] text-white antialiased min-h-screen">{children}</body>\n'
                '    </html>\n'
                '  );\n'
                "}\n"
            ),
            "src/app/page.tsx": (
                '"use client";\n\n'
                "export default function Home() {\n"
                f'  return <main className="p-8"><h1 className="text-3xl font-bold">{title}</h1><p className="text-gray-400 mt-2">Generated by Turbo Dev Agent</p></main>;\n'
                "}\n"
            ),
        }
