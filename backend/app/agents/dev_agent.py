"""Turbo Dev Agent — specialist agent for development task operations.

Delegates code generation to sandbox containers via the sandbox service.
Each sandbox runs Copilot CLI with OpenSpec workflow for iterative development.

Supports two pipeline modes:
- Mockup: single iteration from full spec → GUI-only mockup app
- OpenSpec: iterative spec-driven development (foundation → parallel features)
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx

from app.models.dev_task import DevArtifact, DevDecision
from app.services.dev_service import InMemoryDevService, _default_iteration

logger = logging.getLogger(__name__)

USE_CLI_SANDBOX = os.environ.get("USE_CLI_SANDBOX", "true").lower() == "true"
SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")

# ── Pipeline output buffers (module-level, keyed by dev task ID) ──────────
# Stores streaming output entries for the frontend terminal view.
_pipeline_outputs: dict[str, list[dict]] = {}

# Question patterns that indicate the CLI is waiting for user input
_QUESTION_PATTERNS = [
    r"\?\s*$",                          # ends with ?
    r"\(y/n\)",                          # (y/n)
    r"\(Y/n\)",                          # (Y/n)
    r"\(y/N\)",                          # (y/N)
    r"\[y/N\]",                          # [y/N]
    r"\[Y/n\]",                          # [Y/n]
    r"\[yes/no\]",                       # [yes/no]
    r":\s*$",                            # ends with :
    r">\s*$",                            # ends with >
    r"Press Enter",                      # Press Enter to continue
    r"Do you want to",                   # Do you want to ...
    r"Would you like",                   # Would you like ...
    r"Enter a value",                    # Enter a value for ...
    r"Select.*:",                        # Select an option:
    r"Choose.*:",                        # Choose ...
    r"Overwrite.*\?",                    # Overwrite file?
    r"proceed\?",                        # proceed?
]
_QUESTION_RE = re.compile("|".join(_QUESTION_PATTERNS), re.IGNORECASE)


def get_pipeline_output(task_id: str) -> list[dict]:
    """Get the pipeline output buffer for a task (for SSE streaming)."""
    return _pipeline_outputs.get(task_id, [])


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

        # Initialize pipeline output buffer for terminal streaming
        _pipeline_outputs[task_id] = []

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
            # Emit error to terminal
            if task_id in _pipeline_outputs:
                _pipeline_outputs[task_id].append({
                    "type": "stderr", "data": f"Pipeline failed: {e}", "ts": time.time()
                })
            try:
                await service.set_status(task_id, "failed")
            except Exception:
                logger.exception(
                    "Failed to set error status on task %s after pipeline failure", task_id
                )
        finally:
            # Emit completion marker
            if task_id in _pipeline_outputs:
                _pipeline_outputs[task_id].append({
                    "type": "exit", "code": 0, "ts": time.time()
                })

    async def _run_mockup_pipeline(self, task_id: str, user_id: str) -> None:
        """Mockup pipeline: openspec init → propose → apply → archive → screenshots."""
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)

        spec_content = await self._get_spec_content(task.spec_id, user_id)
        mockup_desc = self._extract_mockup_description(spec_content)
        model = await self._get_user_model(user_id)

        # Each dev task gets its own dedicated workspace directory
        work_dir = f"/workspace/{task_id}"
        await self._sandbox_exec(
            task_id=task_id,
            command=f"rm -rf {work_dir} && mkdir -p {work_dir}",
            args=[],
            stage_label="cleanup",
            raise_on_error=False,
        )

        # Stage: init — openspec init sets up skills for Copilot CLI
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("Mockup init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            task_id=task_id,
            command="openspec",
            args=["init", "--tools", "github-copilot", "--force"],
            stage_label="init",
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        # Stage: propose — Copilot CLI proposes the mockup via openspec-propose
        await svc.set_iteration_stage_status(task_id, 0, "propose", "running")
        logger.info("Mockup propose: task=%s, desc_len=%d", task_id, len(mockup_desc))
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Use the openspec-propose skill to create a complete proposal "
                "for this mockup application. Generate design, specs, and tasks.\n\n"
                f"{mockup_desc}"
            ),
            model=model,
            stage_label="propose",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "propose", "completed")

        # Stage: apply — Copilot CLI implements the proposal via openspec-apply
        await svc.set_iteration_stage_status(task_id, 0, "apply", "running")
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Use the openspec-apply-change skill to implement all tasks "
                "from the proposal. Work through every task until all are complete. "
                "Fix any build errors along the way."
            ),
            model=model,
            stage_label="apply",
            stall_timeout=180,
            raise_on_error=False,
            work_dir=work_dir,
        )
        await self._checkpoint(task_id, "mockup-apply", work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "apply", "completed")

        # Stage: archive — Copilot CLI archives the completed change
        await svc.set_iteration_stage_status(task_id, 0, "archive", "running")
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Use the openspec-archive-change skill to archive the completed "
                "change. Update the generic specs with the final state."
            ),
            model=model,
            stage_label="archive",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "archive", "completed")

        # Stage: screenshots — Copilot CLI starts app + captures with Playwright
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "running")
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Look at the project in the current directory. "
                "Find the main application entry point and figure out how to start it. "
                "Then:\n"
                "1. Install dependencies if needed (npm install or pip install etc)\n"
                "2. Start the app in background (e.g. `npm run dev &` or `npx serve . &`)\n"
                "3. Wait a few seconds for it to be ready\n"
                "4. Take a screenshot with: npx playwright screenshot "
                f"http://localhost:3000 {work_dir}/screenshot.png "
                "--full-page --wait-for-timeout=5000\n"
                "5. If port 3000 doesn't work, check package.json for the correct port\n"
                "6. If the app has no dev server, try `npx serve . -l 3000 &` to serve static files\n"
                "Save screenshots as PNG files in the current directory."
            ),
            model=model,
            stage_label="screenshots",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await self._collect_screenshots(task_id, work_dir=work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await svc.set_status(task_id, "completed")
        logger.info("Mockup pipeline COMPLETED for task %s", task_id)

    async def _run_openspec_pipeline(self, task_id: str, user_id: str) -> None:
        """OpenSpec pipeline: init → foundation propose/apply → features → archive → screenshots."""
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)

        spec_content = await self._get_spec_content(task.spec_id, user_id)
        foundation_prompt, feature_prompts = self._extract_openspec_config(spec_content)
        model = await self._get_user_model(user_id)

        # Each dev task gets its own dedicated workspace directory
        work_dir = f"/workspace/{task_id}"
        await self._sandbox_exec(
            task_id=task_id,
            command=f"rm -rf {work_dir} && mkdir -p {work_dir}",
            args=[],
            stage_label="cleanup",
            raise_on_error=False,
        )

        # ── Foundation: init → propose → apply ───────────────────────
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("OpenSpec init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            task_id=task_id,
            command="openspec",
            args=["init", "--tools", "github-copilot", "--force"],
            stage_label="init",
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        await svc.set_iteration_stage_status(task_id, 0, "propose", "running")
        logger.info("OpenSpec foundation propose: task=%s", task_id)
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Use the openspec-propose skill to create a proposal for the "
                "foundation of this application. Generate design, specs, and tasks.\n\n"
                f"{foundation_prompt}"
            ),
            model=model,
            stage_label="foundation-propose",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "propose", "completed")

        await self._checkpoint(task_id, "foundation-propose", work_dir)

        await svc.set_iteration_stage_status(task_id, 0, "apply", "running")
        # Try task-by-task apply: read tasks.md, apply individually with checkpoints
        task_titles = await self._parse_openspec_tasks(work_dir)
        if len(task_titles) > 1:
            logger.info(
                "Decomposed apply into %d tasks: %s",
                len(task_titles),
                [t[:50] for t in task_titles],
            )
            for t_idx, t_title in enumerate(task_titles):
                logger.info(
                    "Apply task %d/%d: %s", t_idx + 1, len(task_titles), t_title
                )
                await self._sandbox_exec(
                    task_id=task_id,
                    prompt=(
                        "Use the openspec-apply-change skill. Focus on completing "
                        "the next incomplete task from the proposal. Do NOT skip "
                        "ahead to other tasks. Once this task is done, stop.\n\n"
                        f"Current task: {t_title}"
                    ),
                    model=model,
                    stage_label=f"foundation-apply-{t_idx + 1}",
                    timeout=600,
                    stall_timeout=180,
                    raise_on_error=False,
                    work_dir=work_dir,
                )
                await self._checkpoint(task_id, f"foundation-task-{t_idx + 1}", work_dir)
        else:
            # Fallback: single apply if we couldn't parse tasks
            await self._sandbox_exec(
                task_id=task_id,
                prompt=(
                    "Use the openspec-apply-change skill to implement all tasks "
                    "from the foundation proposal. Work through every task until done. "
                    "Fix any build errors along the way."
                ),
                model=model,
                stage_label="foundation-apply",
                stall_timeout=180,
                raise_on_error=False,
                work_dir=work_dir,
            )
            await self._checkpoint(task_id, "foundation-apply", work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "apply", "completed")

        # ── Post-foundation hook: pick up any queued feature iterations ──
        # Features may have been added via add_feature_to_spec while foundation was running
        task = await svc.get_by_id(task_id)
        queued_iterations = []
        if task:
            for it in task.iterations:
                if it.iteration_index > len(feature_prompts) and hasattr(it, '_raw_data'):
                    queued_iterations.append(it)

        # ── Features: parallel propose/apply ─────────────────────────
        # Each feature runs in the same work_dir (sequential OpenSpec changes)
        # but propose/apply pairs are still sequential since they build on each other
        for idx, feat_prompt in enumerate(feature_prompts):
            iter_idx = idx + 1
            await svc.set_iteration_stage_status(
                task_id, iter_idx, "propose", "running"
            )
            logger.info(
                "OpenSpec feature propose: task=%s, iter=%d", task_id, iter_idx
            )
            await self._sandbox_exec(
                task_id=task_id,
                prompt=(
                    "Use the openspec-propose skill to create a proposal for "
                    "adding this feature to the existing application.\n\n"
                    f"{feat_prompt}"
                ),
                model=model,
                stage_label=f"feature-{iter_idx}-propose",
                raise_on_error=False,
                work_dir=work_dir,
            )
            await svc.set_iteration_stage_status(
                task_id, iter_idx, "propose", "completed"
            )
            await svc.set_iteration_stage_status(
                task_id, iter_idx, "apply", "running"
            )
            # Try task-by-task apply for features too
            feat_tasks = await self._parse_openspec_tasks(work_dir)
            if len(feat_tasks) > 1:
                for ft_idx, ft_title in enumerate(feat_tasks):
                    await self._sandbox_exec(
                        task_id=task_id,
                        prompt=(
                            "Use the openspec-apply-change skill. Focus on completing "
                            "the next incomplete task from the latest proposal. Do NOT "
                            "skip ahead to other tasks. Once this task is done, stop.\n\n"
                            f"Current task: {ft_title}"
                        ),
                        model=model,
                        stage_label=f"feature-{iter_idx}-apply-{ft_idx + 1}",
                        timeout=600,
                        stall_timeout=180,
                        raise_on_error=False,
                        work_dir=work_dir,
                    )
                    await self._checkpoint(
                        task_id, f"feature-{iter_idx}-task-{ft_idx + 1}", work_dir
                    )
            else:
                await self._sandbox_exec(
                    task_id=task_id,
                    prompt=(
                        "Use the openspec-apply-change skill to implement all tasks "
                        "from the latest proposal. Work through every task until done. "
                        "Fix any build errors."
                    ),
                    model=model,
                    stage_label=f"feature-{iter_idx}-apply",
                    stall_timeout=180,
                    raise_on_error=False,
                    work_dir=work_dir,
                )
                await self._checkpoint(
                    task_id, f"feature-{iter_idx}-apply", work_dir
                )
            await svc.set_iteration_stage_status(
                task_id, iter_idx, "apply", "completed"
            )

        # ── Execute any queued iterations added during pipeline ──────
        task = await svc.get_by_id(task_id)
        if task:
            known_count = len(feature_prompts) + 1  # foundation + original features
            for it in task.iterations:
                if it.iteration_index >= known_count:
                    # This is a dynamically added feature — check for stored instruction
                    doc = svc._store.get(task_id) if hasattr(svc, '_store') else None
                    propose_instr = ""
                    if doc:
                        for it_doc in doc.get("iterations", []):
                            if it_doc["iterationIndex"] == it.iteration_index:
                                propose_instr = it_doc.get("proposeInstruction", "")
                                break
                    if propose_instr:
                        await self.run_incremental_feature_pipeline(
                            task_id, it.iteration_index, propose_instr, user_id
                        )

        # ── Archive ──────────────────────────────────────────────────
        await svc.set_iteration_stage_status(task_id, 0, "archive", "running")
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Use the openspec-archive-change skill to archive the completed "
                "change. Update the generic specs with the final state."
            ),
            model=model,
            stage_label="archive",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await svc.set_iteration_stage_status(task_id, 0, "archive", "completed")

        # ── Screenshots — Copilot CLI starts app + captures ─────────
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "running")
        await self._sandbox_exec(
            task_id=task_id,
            prompt=(
                "Look at the project in the current directory. "
                "Find the main application entry point and figure out how to start it. "
                "Then:\n"
                "1. Install dependencies if needed (npm install or pip install etc)\n"
                "2. Start the app in background (e.g. `npm run dev &` or `npx serve . &`)\n"
                "3. Wait a few seconds for it to be ready\n"
                "4. Take a screenshot with: npx playwright screenshot "
                f"http://localhost:3000 {work_dir}/screenshot.png "
                "--full-page --wait-for-timeout=5000\n"
                "5. If port 3000 doesn't work, check package.json for the correct port\n"
                "6. If the app has no dev server, try `npx serve . -l 3000 &` to serve static files\n"
                "Save screenshots as PNG files in the current directory."
            ),
            model=model,
            stage_label="screenshots",
            raise_on_error=False,
            work_dir=work_dir,
        )
        await self._collect_screenshots(task_id, work_dir=work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await svc.set_status(task_id, "completed")
        logger.info("OpenSpec pipeline COMPLETED for task %s", task_id)

    # ── Incremental feature addition ─────────────────────────────

    async def append_feature_iteration(
        self,
        task_id: str,
        feature_name: str,
        propose_instruction: str,
        spec_id: str,
        user_id: str = "default-user",
    ) -> dict:
        """Append a new feature iteration to an existing OpenSpec dev task.

        Returns dict with 'extended' and 'pipeline_triggered' booleans.
        """
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)
        if not task:
            return {"error": "Dev task not found", "extended": False, "pipeline_triggered": False}
        if task.mode != "openspec":
            return {"error": "Only openspec mode supports incremental features", "extended": False, "pipeline_triggered": False}

        # Determine foundation status
        foundation_completed = False
        if task.iterations:
            foundation = task.iterations[0]
            foundation_completed = all(
                s.status == "completed" for s in foundation.stages
                if s.name in ("init", "propose", "apply")
            )

        # Create the new iteration
        iteration_data = _default_iteration(0, f"Feature: {feature_name}", spec_id)
        # Store the propose instruction in the iteration for later use
        iteration_data["proposeInstruction"] = propose_instruction
        new_index = await svc.add_iteration(task_id, iteration_data)
        if new_index is None:
            return {"error": "Failed to add iteration", "extended": False, "pipeline_triggered": False}

        # Trigger pipeline if foundation is done
        pipeline_triggered = False
        if foundation_completed and task.status in ("completed", "running"):
            pipeline_triggered = True
            asyncio.create_task(
                self.run_incremental_feature_pipeline(
                    task_id, new_index, propose_instruction, user_id
                )
            )

        logger.info(
            "Appended feature iteration %d to task %s: %s (pipeline_triggered=%s)",
            new_index, task_id, feature_name, pipeline_triggered,
        )
        return {"extended": True, "pipeline_triggered": pipeline_triggered, "iteration_index": new_index}

    async def run_incremental_feature_pipeline(
        self,
        task_id: str,
        iteration_index: int,
        propose_instruction: str,
        user_id: str = "default-user",
    ) -> None:
        """Run pipeline for a single incrementally-added feature in the existing workspace."""
        svc = self._service.with_user(user_id)
        model = await self._get_user_model(user_id)

        # Initialize output buffer if not present
        if task_id not in _pipeline_outputs:
            _pipeline_outputs[task_id] = []

        # Update task status to running if it was completed
        task = await svc.get_by_id(task_id)
        if task and task.status == "completed":
            await svc.set_status(task_id, "running")

        # Determine workspace from foundation iteration
        work_dir = "/workspace"
        if task and task.iterations:
            foundation_ws = task.iterations[0].workspace_path
            if foundation_ws:
                work_dir = foundation_ws

        try:
            # Propose
            await svc.set_iteration_stage_status(task_id, iteration_index, "propose", "running")
            logger.info("Incremental feature propose: task=%s, iter=%d", task_id, iteration_index)
            await self._sandbox_exec(
                task_id=task_id,
                prompt=(
                    "Use the openspec-propose skill to create a proposal for "
                    "adding this feature to the existing application.\n\n"
                    f"{propose_instruction}"
                ),
                model=model,
                stage_label=f"feature-{iteration_index}-propose",
                work_dir=work_dir,
            )
            await svc.set_iteration_stage_status(task_id, iteration_index, "propose", "completed")

            # Apply
            await svc.set_iteration_stage_status(task_id, iteration_index, "apply", "running")
            await self._sandbox_exec(
                task_id=task_id,
                prompt=(
                    "Use the openspec-apply-change skill to implement all tasks "
                    "from the latest proposal. Work through every task until done. "
                    "Fix any build errors."
                ),
                model=model,
                stage_label=f"feature-{iteration_index}-apply",
                work_dir=work_dir,
            )
            await svc.set_iteration_stage_status(task_id, iteration_index, "apply", "completed")

            # Screenshots
            await svc.set_iteration_stage_status(task_id, iteration_index, "screenshots", "running")
            await self._sandbox_exec(
                task_id=task_id,
                prompt=(
                    "Take screenshots of the updated application. "
                    "Start the app in the background (e.g. npm run dev &). "
                    "Wait for it to be ready, then use "
                    "'npx playwright screenshot http://localhost:3000 "
                    f"{work_dir}/screenshot-feature-{iteration_index}.png --full-page "
                    "--wait-for-timeout=5000'. "
                    "If the app uses a different port, adjust accordingly."
                ),
                model=model,
                stage_label=f"feature-{iteration_index}-screenshots",
                raise_on_error=False,
                work_dir=work_dir,
            )
            await self._collect_screenshots(task_id, work_dir=work_dir)
            await svc.set_iteration_stage_status(task_id, iteration_index, "screenshots", "completed")

            # Check if all iterations are done — if so, mark task completed
            task = await svc.get_by_id(task_id)
            if task:
                all_done = all(
                    all(s.status == "completed" for s in it.stages if s.name in ("propose", "apply"))
                    for it in task.iterations
                )
                if all_done:
                    await svc.set_status(task_id, "completed")

            logger.info("Incremental feature pipeline COMPLETED: task=%s, iter=%d", task_id, iteration_index)

        except Exception as e:
            logger.exception("Incremental feature pipeline FAILED: task=%s, iter=%d", task_id, iteration_index)
            try:
                await svc.set_iteration_stage_status(
                    task_id, iteration_index, "apply", "failed", error=str(e)
                )
            except Exception:
                pass

    # ── Sandbox HTTP helpers ───────────────────────────────────────

    async def _sandbox_exec(
        self,
        *,
        task_id: str = "",
        prompt: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        model: str = "claude-opus-4.6",
        stage_label: str = "",
        timeout: float = 1200,
        stall_timeout: float = 180,
        raise_on_error: bool = True,
        work_dir: str = "/workspace",
    ) -> str:
        """Submit a task to the sandbox and stream output via SSE.

        Streams real-time output into the pipeline buffer for the terminal view.
        Detects CLI questions and auto-answers them using the model.
        Returns combined stdout output.

        Args:
            stall_timeout: Seconds of silence (no stdout) before considering the
                task stalled and killing it. Default 180s (3 minutes).
        """
        payload: dict = {"workDir": work_dir}
        if prompt:
            payload["prompt"] = prompt
            payload["model"] = model
        elif command:
            payload["command"] = command
            payload["args"] = args or []
        else:
            raise ValueError("prompt or command is required")

        log_preview = prompt[:120] if prompt else f"{command} {args}"
        logger.info("Sandbox exec [%s]: %s", stage_label, log_preview)

        # Ensure pipeline output buffer exists
        if task_id and task_id not in _pipeline_outputs:
            _pipeline_outputs[task_id] = []
        output_buf = _pipeline_outputs.get(task_id, [])

        # Emit stage marker
        if task_id:
            output_buf.append({
                "type": "stage", "data": f"── {stage_label} ──", "ts": time.time()
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{SANDBOX_URL}/tasks", json=payload)
            resp.raise_for_status()
            task_data = resp.json()
            sandbox_task_id = task_data["id"]

        # Stream output via SSE
        start = time.monotonic()
        last_output_time = time.monotonic()
        exit_code = -1
        output_lines: list[str] = []
        accumulated_text = ""

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET", f"{SANDBOX_URL}/tasks/{sandbox_task_id}/stream"
                ) as sse_resp:
                    async for raw_line in sse_resp.aiter_lines():
                        now = time.monotonic()
                        if now - start > timeout:
                            raise RuntimeError(
                                f"Sandbox task timed out: {stage_label}"
                            )
                        # Stall detection: no meaningful output for too long
                        if now - last_output_time > stall_timeout:
                            raise RuntimeError(
                                f"Sandbox task stalled (no output for "
                                f"{stall_timeout:.0f}s): {stage_label}"
                            )

                        if not raw_line.startswith("data: "):
                            continue

                        try:
                            entry = json.loads(raw_line[6:])
                        except json.JSONDecodeError:
                            continue

                        entry_type = entry.get("type", "")

                        # Forward to pipeline buffer for terminal view
                        # (skip exit events — the pipeline emits its own on completion)
                        if task_id and entry_type != "exit":
                            output_buf.append(entry)

                        if entry_type == "stdout":
                            data = entry.get("data", "")
                            output_lines.append(data)
                            accumulated_text += data
                            if data.strip():
                                last_output_time = now

                            # Detect questions and auto-answer
                            if _QUESTION_RE.search(accumulated_text.strip()):
                                await self._auto_answer(
                                    sandbox_task_id=sandbox_task_id,
                                    question=accumulated_text.strip(),
                                    stage_label=stage_label,
                                    task_id=task_id,
                                    model=model,
                                    output_buf=output_buf,
                                )
                                accumulated_text = ""

                        elif entry_type == "stderr":
                            data = entry.get("data", "")
                            if data.strip():
                                last_output_time = now

                        elif entry_type == "exit":
                            exit_code = entry.get("code", -1)
                            break

        except httpx.HTTPError as e:
            logger.warning(
                "SSE stream error [%s], falling back to polling: %s",
                stage_label, e,
            )
            # Fallback: poll for completion
            exit_code = await self._poll_until_done(
                sandbox_task_id, stage_label, timeout - (time.monotonic() - start),
                output_lines, output_buf, task_id,
            )

        combined = "".join(output_lines)
        logger.info(
            "Sandbox exec [%s] exit=%d (%d chars output)",
            stage_label, exit_code, len(combined),
        )

        if exit_code != 0 and raise_on_error:
            raise RuntimeError(
                f"Sandbox task [{stage_label}] failed with exit code {exit_code}"
            )

        return combined

    async def _checkpoint(
        self,
        task_id: str,
        label: str,
        work_dir: str,
    ) -> None:
        """Git commit all current work as a checkpoint (preserves progress)."""
        try:
            await self._sandbox_exec(
                task_id=task_id,
                command="bash",
                args=[
                    "-c",
                    f"cd {work_dir} && git add -A && "
                    f'git diff --cached --quiet || git commit -m "checkpoint: {label}"',
                ],
                stage_label=f"checkpoint-{label}",
                timeout=30,
                stall_timeout=20,
                raise_on_error=False,
            )
        except Exception as e:
            logger.debug("Checkpoint failed (non-critical): %s", e)

    async def _read_sandbox_file(self, path: str) -> str | None:
        """Read a text file from the sandbox container via HTTP."""
        # The /files/* endpoint serves from /workspace, so strip the prefix
        rel_path = path
        if rel_path.startswith("/workspace/"):
            rel_path = rel_path[len("/workspace/"):]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{SANDBOX_URL}/files/{rel_path}")
                if resp.status_code == 200:
                    data = resp.json()
                    return base64.b64decode(data["data"]).decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug("Could not read sandbox file %s: %s", path, e)
        return None

    async def _parse_openspec_tasks(self, work_dir: str) -> list[str]:
        """Read tasks.md from sandbox and extract individual task titles."""
        content = await self._read_sandbox_file(f"{work_dir}/openspec/changes")
        if not content:
            return []
        # Find the active change directory
        # tasks.md lives at openspec/changes/<name>/tasks.md
        # Try to find it via listing
        try:
            output = await self._sandbox_exec(
                command="bash",
                args=["-c", f"find {work_dir}/openspec/changes -name tasks.md 2>/dev/null | head -1"],
                stage_label="find-tasks",
                timeout=15,
                stall_timeout=10,
                raise_on_error=False,
            )
            tasks_path = output.strip()
            if not tasks_path:
                return []
            tasks_content = await self._read_sandbox_file(tasks_path)
            if not tasks_content:
                return []
            # Parse task titles from markdown: lines starting with "- [ ]" or "### "
            tasks = re.findall(
                r"^(?:- \[[ x]\] |### )(.+)$", tasks_content, re.MULTILINE
            )
            return tasks
        except Exception as e:
            logger.debug("Could not parse tasks: %s", e)
            return []

    async def _auto_answer(
        self,
        *,
        sandbox_task_id: str,
        question: str,
        stage_label: str,
        task_id: str,
        model: str,
        output_buf: list[dict],
    ) -> None:
        """Detect a CLI question and auto-answer it."""
        # Generate answer using a simple heuristic + context
        answer = self._generate_quick_answer(question)
        logger.info(
            "Auto-answer [%s]: Q=%s → A=%s",
            stage_label, question[-100:], answer,
        )

        # Send answer to sandbox stdin
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{SANDBOX_URL}/tasks/{sandbox_task_id}/input",
                    json={"input": answer},
                )
                resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to send auto-answer: %s", e)
            return

        # Log to output buffer
        output_buf.append({
            "type": "decision",
            "data": f"🤖 Auto-answered: {answer}",
            "ts": time.time(),
        })

        # Store decision in the dev task
        if task_id:
            try:
                svc = self._service.with_user("default-user")
                task = await svc.get_by_id(task_id)
                if task:
                    decision = DevDecision(
                        question=question[-500:],
                        answer=answer,
                        stage=stage_label,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    task.decisions.append(decision)
            except Exception as e:
                logger.debug("Could not store decision: %s", e)

    @staticmethod
    def _generate_quick_answer(question: str) -> str:
        """Generate a quick answer to a CLI question using heuristics."""
        q_lower = question.lower().strip()

        # Common yes/no patterns — default to yes (proceed)
        if any(p in q_lower for p in [
            "(y/n)", "[y/n]", "(yes/no)", "[yes/no]",
            "do you want to", "would you like", "overwrite",
            "proceed?", "continue?",
        ]):
            return "y"

        # Press Enter to continue
        if "press enter" in q_lower:
            return ""

        # Select/choose — pick first option or default
        if any(p in q_lower for p in ["select", "choose"]):
            return "1"

        # Default: press Enter (accept default)
        return ""

    async def _poll_until_done(
        self,
        sandbox_task_id: str,
        stage_label: str,
        remaining_timeout: float,
        output_lines: list[str],
        output_buf: list[dict],
        task_id: str,
    ) -> int:
        """Fallback polling when SSE fails."""
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=15.0) as client:
            while time.monotonic() - start < remaining_timeout:
                await asyncio.sleep(3)
                try:
                    resp = await client.get(
                        f"{SANDBOX_URL}/tasks/{sandbox_task_id}/status"
                    )
                    resp.raise_for_status()
                    status = resp.json()
                except Exception:
                    continue

                if status.get("done"):
                    for entry in status.get("recentOutput", []):
                        if entry.get("type") == "stdout":
                            data = entry.get("data", "")
                            output_lines.append(data)
                        if task_id:
                            output_buf.append(entry)
                    return status.get("exitCode", -1)

        raise RuntimeError(f"Sandbox task timed out: {stage_label}")

    async def _collect_screenshots(self, task_id: str, work_dir: str = "/workspace") -> None:
        """Fetch screenshot PNGs from the sandbox workspace and store as artifacts."""
        svc = self._service
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Search for screenshot*.png files specifically
                resp = await client.get(
                    f"{SANDBOX_URL}/files",
                    params={"glob": "screenshot*.png", "dir": work_dir},
                )
                resp.raise_for_status()
                files = resp.json().get("files", [])
                # Also search for any *.png at the root of work_dir
                if not files:
                    resp2 = await client.get(
                        f"{SANDBOX_URL}/files",
                        params={"glob": "*.png", "dir": work_dir},
                    )
                    resp2.raise_for_status()
                    files = resp2.json().get("files", [])
                logger.info("Found %d screenshot files in sandbox", len(files))

                for file_path in files:
                    # file_path is absolute, e.g. /workspace/abc/screenshot.png
                    # sandbox /files/* joins with /workspace, so strip that prefix
                    rel = file_path.replace("/workspace/", "", 1)
                    try:
                        fresp = await client.get(f"{SANDBOX_URL}/files/{rel}")
                        fresp.raise_for_status()
                        fdata = fresp.json()
                        artifact = DevArtifact(
                            type="screenshot",
                            name=fdata.get("name", rel),
                            data=fdata.get("data", ""),
                        )
                        await svc.add_artifact(task_id, artifact)
                        logger.info("Stored screenshot artifact: %s", rel)
                    except Exception as e:
                        logger.warning("Failed to fetch screenshot %s: %s", rel, e)
        except Exception as e:
            logger.warning("Failed to list screenshot files: %s", e)

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
        return "claude-opus-4.6"
