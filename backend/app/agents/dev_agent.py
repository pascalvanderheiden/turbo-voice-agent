"""Turbo Dev Agent — specialist agent for development task operations.

Delegates code generation to sandbox containers via the sandbox service.
Each sandbox runs Copilot CLI with OpenSpec workflow for iterative development.

Supports two pipeline modes:
- Mockup: single iteration from full spec → GUI-only mockup app
- OpenSpec: iterative spec-driven development (foundation → parallel features)
"""

import asyncio
import json
import logging
import os
import re

import httpx

from app.services.dev_service import InMemoryDevService, _default_iteration

logger = logging.getLogger(__name__)

USE_CLI_SANDBOX = os.environ.get("USE_CLI_SANDBOX", "true").lower() == "true"
SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")


class DevAgent:
    """Agent that handles development task operations."""

    def __init__(
        self,
        dev_service: InMemoryDevService,
        spec_service=None,
        skills_service=None,
        sandbox_service=None,
    ):
        self._service = dev_service
        self._spec_service = spec_service
        self._skills_service = skills_service
        self._sandbox_service = sandbox_service

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
                            "mode": {"type": "string", "enum": ["mockup", "openspec"], "description": "Pipeline mode: mockup (quick GUI) or openspec (iterative)"},
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
                    "description": "Start the development pipeline for a task. Mockup mode = quick GUI mockup. OpenSpec mode = iterative spec-driven development.",
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

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        """Execute a function call and return the result as a string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        service = self._service.with_user(user_id)

        if function_name == "create_dev_task":
            from app.models.dev_task import DevTaskCreate
            mode = args.get("mode", "mockup")
            task = await service.create(
                DevTaskCreate(title=args["title"], specId=args.get("spec_id"), mode=mode)
            )
            # If linked to a spec, populate iterations and set bidirectional link
            if args.get("spec_id") and self._spec_service:
                try:
                    await self._populate_iterations_from_spec(task.id, args["spec_id"], mode, user_id=user_id)
                    await self._spec_service.with_user(user_id).set_dev_task_id(args["spec_id"], task.id, "in-development")
                except Exception:
                    logger.exception("Failed to populate iterations / link spec for task %s", task.id)
            # Auto-attach relevant skills based on title + spec content
            try:
                await self._auto_attach_skills(task.id, args["title"], args.get("spec_id"), user_id=user_id)
            except Exception:
                logger.exception("Failed to auto-attach skills for task %s", task.id)
            task = await service.get_by_id(task.id)
            return json.dumps({"success": True, "task": {"id": task.id, "title": task.title, "mode": task.mode}})

        elif function_name == "get_dev_tasks":
            tasks = await service.list()
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
            task = await service.get_by_id(args["task_id"])
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
            deleted = await service.delete(args["task_id"])
            return json.dumps({"success": deleted})

        elif function_name == "trigger_dev_pipeline":
            task = await service.get_by_id(args["task_id"])
            if not task:
                return json.dumps({"error": "Dev task not found"})
            if task.status not in ("pending", "failed"):
                return json.dumps({"error": "Task already running or completed"})
            await service.set_status(args["task_id"], "running")
            asyncio.create_task(self.run_pipeline(args["task_id"], user_id=user_id))
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

        if mode == "mockup":
            # Single iteration for the full mockup
            full_label = f"Mockup: {spec.title}"
            iterations = [_default_iteration(0, full_label, spec_id)]
        else:
            # OpenSpec: foundation first, then each feature from spec content
            iterations = [_default_iteration(0, f"Foundation: {spec.title}", spec_id)]
            # Parse feature prompts from spec content if available
            spec_content = spec.content or ""
            for i, match in enumerate(
                re.finditer(
                    r'#### Feature: (.+?)\n(.*?)(?=\n#### Feature:|\n### |\n## |\Z)',
                    spec_content,
                    re.DOTALL,
                )
            ):
                feature_title = match.group(1).strip()
                iterations.append(_default_iteration(i + 1, f"Feature: {feature_title}", spec_id))
            # Fallback: if no features parsed from content, use sub-specs
            if len(iterations) == 1:
                features = await spec_svc.get_features_for_foundation(spec_id)
                for i, f in enumerate(features):
                    iterations.append(_default_iteration(i + 1, f"Feature: {f.title}", f.id))

        dev_svc = self._service.with_user(user_id) if user_id else self._service
        await dev_svc.set_iterations(task_id, iterations)

    # ── Pipeline execution ──────────────────────────────────────────

    async def run_pipeline(self, task_id: str, user_id: str = "default-user") -> None:
        """Run the pipeline based on task mode, delegating to sandbox."""
        logger.info("Pipeline starting: task=%s, user=%s", task_id, user_id)
        service = self._service.with_user(user_id)

        if not USE_CLI_SANDBOX:
            logger.warning("CLI sandbox disabled — skipping pipeline for task %s", task_id)
            await service.set_status(task_id, "completed")
            return

        try:
            task = await service.get_by_id(task_id)
            if not task:
                logger.error("Pipeline aborted: task %s not found", task_id)
                return

            if task.mode == "openspec" and len(task.iterations) > 1:
                await self._run_openspec_pipeline(task_id, user_id)
            else:
                await self._run_mockup_pipeline(task_id, user_id)

        except Exception as e:
            logger.exception("Pipeline FAILED for task %s: %s", task_id, str(e))
            try:
                await service.set_status(task_id, "failed")
            except Exception:
                logger.exception(
                    "Failed to set error status on task %s after pipeline failure", task_id
                )

    async def _run_mockup_pipeline(self, task_id: str, user_id: str) -> None:
        """Mockup pipeline: openspec init → propose → apply → screenshots."""
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)

        spec_content = await self._get_spec_content(task.spec_id, user_id)
        mockup_desc = self._extract_mockup_description(spec_content)
        model = await self._get_user_model(user_id)

        # Stage: init — initialize openspec project in sandbox
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("Mockup init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            prompt="Initialize a new Next.js project with TypeScript and Tailwind CSS. "
            "Set up the basic project structure.",
            model=model,
            stage_label="init",
        )
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        # Stage: propose — send mockup description to Copilot CLI
        await svc.set_iteration_stage_status(task_id, 0, "propose", "running")
        logger.info("Mockup propose: task=%s, desc_len=%d", task_id, len(mockup_desc))
        await self._sandbox_exec(
            prompt=f"Build a mockup application based on this description:\n\n{mockup_desc}",
            model=model,
            stage_label="propose",
        )
        await svc.set_iteration_stage_status(task_id, 0, "propose", "completed")

        # Stage: apply — install deps and verify build
        await svc.set_iteration_stage_status(task_id, 0, "apply", "running")
        await self._sandbox_exec(
            prompt="Install all dependencies with npm install, fix any build errors, "
            "and verify the project builds successfully with npm run build.",
            model=model,
            stage_label="apply",
        )
        await svc.set_iteration_stage_status(task_id, 0, "apply", "completed")

        # Stage: screenshots — capture with Playwright (best-effort)
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "running")
        await self._sandbox_exec(
            command="npx",
            args=["playwright", "screenshot", "--wait-for-timeout=3000",
                  "http://localhost:3000", "/workspace/screenshot.png"],
            stage_label="screenshots",
            raise_on_error=False,
        )
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await svc.set_status(task_id, "completed")
        logger.info("Mockup pipeline COMPLETED for task %s", task_id)

    async def _run_openspec_pipeline(self, task_id: str, user_id: str) -> None:
        """OpenSpec pipeline: init → foundation → parallel features → screenshots."""
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)

        spec_content = await self._get_spec_content(task.spec_id, user_id)
        foundation_prompt, feature_prompts = self._extract_openspec_config(spec_content)
        model = await self._get_user_model(user_id)

        # ── Foundation: init → propose → apply ───────────────────────
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("OpenSpec init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            prompt="Initialize a new Next.js project with TypeScript and Tailwind CSS. "
            "Set up the basic project structure.",
            model=model,
            stage_label="init",
        )
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        await svc.set_iteration_stage_status(task_id, 0, "propose", "running")
        logger.info("OpenSpec foundation propose: task=%s", task_id)
        await self._sandbox_exec(
            prompt=f"Build the foundation of the application:\n\n{foundation_prompt}",
            model=model,
            stage_label="foundation-propose",
        )
        await svc.set_iteration_stage_status(task_id, 0, "propose", "completed")

        await svc.set_iteration_stage_status(task_id, 0, "apply", "running")
        await self._sandbox_exec(
            prompt="Install all dependencies, fix any build errors, and verify "
            "the foundation builds successfully.",
            model=model,
            stage_label="foundation-apply",
        )
        await svc.set_iteration_stage_status(task_id, 0, "apply", "completed")

        # ── Features: parallel propose/apply (max 3 concurrent) ──────
        semaphore = asyncio.Semaphore(3)

        async def run_feature(idx: int, prompt: str) -> None:
            async with semaphore:
                iter_idx = idx + 1
                await svc.set_iteration_stage_status(
                    task_id, iter_idx, "propose", "running"
                )
                logger.info(
                    "OpenSpec feature propose: task=%s, iter=%d", task_id, iter_idx
                )
                await self._sandbox_exec(
                    prompt=f"Add this feature to the existing application:\n\n{prompt}",
                    model=model,
                    stage_label=f"feature-{iter_idx}-propose",
                )
                await svc.set_iteration_stage_status(
                    task_id, iter_idx, "propose", "completed"
                )
                await svc.set_iteration_stage_status(
                    task_id, iter_idx, "apply", "running"
                )
                await self._sandbox_exec(
                    prompt="Fix any build errors from the last change and verify "
                    "the project still builds.",
                    model=model,
                    stage_label=f"feature-{iter_idx}-apply",
                )
                await svc.set_iteration_stage_status(
                    task_id, iter_idx, "apply", "completed"
                )

        if feature_prompts:
            await asyncio.gather(
                *[run_feature(i, p) for i, p in enumerate(feature_prompts)]
            )

        # ── Screenshots (best-effort) ────────────────────────────────
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "running")
        await self._sandbox_exec(
            command="npx",
            args=["playwright", "screenshot", "--wait-for-timeout=3000",
                  "http://localhost:3000", "/workspace/screenshot.png"],
            stage_label="screenshots",
            raise_on_error=False,
        )
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await svc.set_status(task_id, "completed")
        logger.info("OpenSpec pipeline COMPLETED for task %s", task_id)

    # ── Sandbox HTTP helpers ───────────────────────────────────────

    async def _sandbox_exec(
        self,
        *,
        prompt: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        model: str = "claude-opus-4.6",
        stage_label: str = "",
        timeout: float = 300,
        raise_on_error: bool = True,
    ) -> str:
        """Submit a task to the sandbox container and wait for completion.

        Returns the combined stdout output. Raises on failure if raise_on_error=True.
        """
        payload: dict = {"workDir": "/workspace"}
        if prompt:
            payload["prompt"] = prompt
            payload["model"] = model
        elif command:
            payload["command"] = command
            payload["args"] = args or []
        else:
            raise ValueError("prompt or command is required")

        logger.info("Sandbox exec [%s]: %s", stage_label, prompt[:120] if prompt else f"{command} {args}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{SANDBOX_URL}/tasks", json=payload)
            resp.raise_for_status()
            task_data = resp.json()
            task_id = task_data["id"]

        # Poll the SSE stream until the task exits
        output_lines: list[str] = []
        exit_code = -1
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                async with client.stream(
                    "GET", f"{SANDBOX_URL}/tasks/{task_id}/stream"
                ) as stream:
                    async for line in stream.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = json.loads(line[6:])
                        if data.get("type") == "stdout":
                            output_lines.append(data.get("data", ""))
                        elif data.get("type") == "stderr":
                            logger.debug(
                                "Sandbox stderr [%s]: %s",
                                stage_label, data.get("data", ""),
                            )
                        elif data.get("type") == "exit":
                            exit_code = data.get("code", -1)
                            break
        except httpx.ReadTimeout:
            logger.error("Sandbox task [%s] timed out after %ds", stage_label, timeout)
            raise RuntimeError(f"Sandbox task timed out: {stage_label}")

        combined = "".join(output_lines)
        logger.info(
            "Sandbox exec [%s] exit=%d (%d chars output)", stage_label, exit_code, len(combined)
        )

        if exit_code != 0 and raise_on_error:
            raise RuntimeError(
                f"Sandbox task [{stage_label}] failed with exit code {exit_code}"
            )

        return combined

    # ── Shared pipeline stages ──────────────────────────────────────

    async def _auto_attach_skills(self, task_id: str, title: str, spec_id: str | None = None, user_id: str | None = None) -> None:
        """Auto-suggest and attach relevant skills to a task based on title + spec content."""
        if not self._skills_service:
            return
        content = title
        if spec_id and self._spec_service:
            spec_svc = self._spec_service.with_user(user_id) if user_id else self._spec_service
            spec = await spec_svc.get_by_id(spec_id)
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

    # ── Spec content helpers ────────────────────────────────────────

    async def _get_spec_content(self, spec_id: str | None, user_id: str) -> str:
        """Get spec content for the given spec_id."""
        if not spec_id or not self._spec_service:
            return ""
        spec = await self._spec_service.with_user(user_id).get_by_id(spec_id)
        return spec.content if spec else ""

    def _extract_mockup_description(self, spec_content: str) -> str:
        """Extract the Mockup Description section from a spec."""
        match = re.search(
            r'## Mockup Description\s*\n(.*?)(?=\n## |\Z)', spec_content, re.DOTALL
        )
        return match.group(1).strip() if match else spec_content

    def _extract_openspec_config(self, spec_content: str) -> tuple[str, list[str]]:
        """Extract foundation and feature prompts from OpenSpec Config section."""
        # Extract foundation prompt
        foundation_match = re.search(
            r'### Foundation\s*\n(.*?)(?=\n### |\Z)', spec_content, re.DOTALL
        )
        foundation = foundation_match.group(1).strip() if foundation_match else ""

        # Extract feature prompts
        features: list[str] = []
        for match in re.finditer(
            r'#### Feature: .+?\n(.*?)(?=\n#### Feature:|\n### |\n## |\Z)',
            spec_content,
            re.DOTALL,
        ):
            features.append(match.group(1).strip())

        return foundation, features

    async def _get_user_model(self, user_id: str) -> str:
        """Get user's configured sandbox model, or default."""
        if self._sandbox_service:
            try:
                svc = self._sandbox_service.with_user(user_id)
                state = await svc.get_status()
                if state and state.config and state.config.model:
                    return state.config.model
            except Exception:
                logger.debug("Failed to read sandbox config for user %s", user_id)
        return "claude-sonnet-4"
