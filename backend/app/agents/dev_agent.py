"""Turbo Dev Agent — specialist agent for development task operations.

Delegates code generation to sandbox containers via the sandbox service.
Each sandbox runs Copilot CLI with simplified sequential pipelines.

Supports two pipeline modes:
- Mockup: single iteration — init → skills → implement → screenshots
- Sequential: multi-iteration — init → skills → implement-foundation → implement-feature-N → screenshots
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
from datetime import UTC, datetime

import httpx

from app.models.dev_task import DevArtifact, DevDecision
from app.services.dev_service import InMemoryDevService, _default_iteration, build_sequential_stages

logger = logging.getLogger(__name__)

USE_CLI_SANDBOX = os.environ.get("USE_CLI_SANDBOX", "true").lower() == "true"
SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")

_DEFAULT_SQUAD_THEME = "Star Wars"

# ── Pipeline output buffers (module-level, keyed by dev task ID) ──────────
# Stores streaming output entries for the frontend terminal view.
_pipeline_outputs: dict[str, list[dict]] = {}
_PIPELINE_BUFFER_CAP = 2000  # Max entries per task to prevent unbounded memory

# ── Active sandbox task IDs per dev task (for cleanup on deletion) ────────
_active_sandbox_tasks: dict[str, str] = {}  # dev_task_id → sandbox_task_id

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


def _buf_append(task_id: str, entry: dict) -> None:
    """Append an entry to the pipeline output buffer, capping at _PIPELINE_BUFFER_CAP."""
    buf = _pipeline_outputs.get(task_id)
    if buf is None:
        return
    buf.append(entry)
    if len(buf) > _PIPELINE_BUFFER_CAP:
        del buf[: len(buf) - _PIPELINE_BUFFER_CAP]


async def cancel_sandbox_task_for(task_id: str) -> bool:
    """Kill any active sandbox task associated with a dev task. Returns True if killed."""
    sandbox_task_id = _active_sandbox_tasks.pop(task_id, None)
    if not sandbox_task_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{SANDBOX_URL}/tasks/{sandbox_task_id}")
            logger.info("Killed sandbox task %s for dev-task %s: %s", sandbox_task_id, task_id, resp.json())
            return True
    except Exception as exc:
        logger.warning("Failed to kill sandbox task %s for dev-task %s: %s", sandbox_task_id, task_id, exc)
        return False


class DevAgent:
    """Agent that handles development task operations."""

    def __init__(
        self,
        dev_service: InMemoryDevService,
        spec_service=None,
        skills_service=None,
        sandbox_service=None,
        cosmos_skills=None,
        slides_service=None,
        profile_service=None,
    ):
        self._service = dev_service
        self._spec_service = spec_service
        self._skills_service = skills_service
        self._sandbox_service = sandbox_service
        self._cosmos_skills = cosmos_skills
        self._slides_service = slides_service
        self._profile_service = profile_service
        self._squad_enabled_tasks: dict[str, bool] = {}  # Task-scoped squad flag

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
                            "mode": {"type": "string", "enum": ["mockup", "sequential", "slides"], "description": "Pipeline mode: mockup (quick GUI), sequential (iterative), or slides (presentation deck)"},
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
                DevTaskCreate(
                    title=args["title"],
                    specId=args.get("spec_id"),
                    slidesId=args.get("slides_id"),
                    mode=mode,
                )
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

        if mode == "slides":
            # Slides mode doesn't populate iterations from spec hierarchy
            return

        if mode == "mockup":
            # Single iteration for the full mockup
            full_label = f"Mockup: {spec.title}"
            iterations = [_default_iteration(0, full_label, spec_id)]
        else:
            # Sequential: foundation first, then each feature from spec content
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

        # Resolve user's GitHub PAT for sandbox auth
        from app.routes.user import get_sandbox_user_token

        self._current_gh_token = await get_sandbox_user_token(user_id)
        self._current_user_id = user_id

        if not USE_CLI_SANDBOX:
            logger.warning("CLI sandbox disabled — skipping pipeline for task %s", task_id)
            await service.set_status(task_id, "completed")
            return

        pipeline_failed = False
        try:
            task = await service.get_by_id(task_id)
            if not task:
                logger.error("Pipeline aborted: task %s not found", task_id)
                return

            if task.mode in ("sequential", "openspec") and len(task.iterations) > 1:
                await self._run_sequential_pipeline(task_id, user_id)
            elif task.mode == "slides":
                await self._run_slides_pipeline(task_id, user_id)
            else:
                await self._run_mockup_pipeline(task_id, user_id)

        except Exception as e:
            pipeline_failed = True
            logger.exception("Pipeline FAILED for task %s: %s", task_id, str(e))
            # Emit error to terminal
            if task_id in _pipeline_outputs:
                _buf_append(task_id, {
                    "type": "stderr", "data": f"Pipeline failed: {e}", "ts": time.time()
                })
            try:
                await service.set_status(task_id, "failed")
                # Mark any running/pending stages as failed so frontend stops spinning
                failed_task = await service.get_by_id(task_id)
                if failed_task:
                    for it in failed_task.iterations:
                        for stage in it.stages:
                            if stage.status in ("running", "pending"):
                                await service.set_iteration_stage_status(
                                    task_id, it.iteration_index, stage.name,
                                    "failed", error=str(e),
                                )
            except Exception:
                logger.exception(
                    "Failed to set error status on task %s after pipeline failure", task_id
                )
        finally:
            # Clean up task-scoped squad flag
            self._squad_enabled_tasks.pop(task_id, None)
            # Always emit exit marker — this is the ONLY way SSE consumers know
            # the pipeline is done. Without this, the frontend stream hangs forever.
            if task_id in _pipeline_outputs:
                buf = _pipeline_outputs[task_id]
                # Only add if not already present (avoid duplicates)
                if not any(e.get("type") == "exit" for e in buf[-5:] if isinstance(e, dict)):
                    _buf_append(task_id, {
                        "type": "exit",
                        "code": 1 if pipeline_failed else 0,
                        "ts": time.time(),
                    })

    async def _run_mockup_pipeline(self, task_id: str, user_id: str) -> None:
        """Mockup pipeline: init → skills → implement → screenshots."""
        self._squad_enabled_tasks[task_id] = False
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

        # Stage: init — workspace setup + squad initialization
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("Mockup init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            task_id=task_id,
            command=(
                f"cd {work_dir} && git init -q"
                " && git config user.email 'agent@sandbox'"
                " && git config user.name 'Sandbox Agent'"
                " && git commit --allow-empty -m 'init' -q"
                " && git remote add origin https://github.com/placeholder/repo.git 2>/dev/null || true"
            ),
            args=[],
            stage_label="init",
            work_dir=work_dir,
            raise_on_error=False,
        )
        await self._run_squad_stage(task_id, work_dir, spec_content, user_id)
        self._squad_enabled_tasks[task_id] = True
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        # Stage: skills — install marketplace + local skills
        await svc.set_iteration_stage_status(task_id, 0, "skills", "running")
        n_skills = await self._install_skills_in_sandbox(
            task_id, task, work_dir, user_id=user_id,
        )
        if n_skills:
            logger.info("Installed %d user skills for task %s", n_skills, task_id)
        else:
            if task_id in _pipeline_outputs:
                _buf_append(task_id, {
                    "type": "stdout", "data": "No skills to install\n", "stage": "skills",
                })
        await svc.set_iteration_stage_status(task_id, 0, "skills", "completed")

        # Stage: implement — single Copilot CLI invocation with autopilot
        await svc.set_iteration_stage_status(task_id, 0, "implement", "running")
        logger.info("Mockup implement: task=%s, desc_len=%d", task_id, len(mockup_desc))
        for attempt in range(2):
            try:
                await self._sandbox_exec(
                    task_id=task_id,
                    prompt=mockup_desc,
                    model=model,
                    stage_label=f"implement{'-retry' if attempt else ''}",
                    stall_timeout=600,
                    timeout=2400,
                    raise_on_error=False,
                    work_dir=work_dir,
                    continue_session=(attempt > 0),
                    agent="squad",
                    autopilot=True,
                )
                break
            except RuntimeError as exc:
                if attempt == 0 and "timed out" in str(exc):
                    logger.warning("Mockup implement timed out, retrying once...")
                    await self._checkpoint(task_id, "mockup-implement-partial", work_dir)
                    if task_id in _pipeline_outputs:
                        _buf_append(task_id, {
                            "type": "stderr",
                            "data": "Implement timed out — retrying with continue...\n",
                            "stage": "implement-retry",
                        })
                else:
                    logger.warning("Mockup implement failed: %s", exc)
                    break
        await self._checkpoint(task_id, "mockup-implement", work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "implement", "completed")

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
                "4. Take screenshots of the key pages/views using Playwright CLI:\n"
                "   npx playwright screenshot --viewport-size='1280,800' "
                f"http://localhost:3000 {work_dir}/screenshot-overview.png\n"
                "5. Navigate to different routes/pages (e.g. /analytics, /reports, /users, "
                "/settings) and take a screenshot of each:\n"
                "   npx playwright screenshot --viewport-size='1280,800' "
                f"http://localhost:3000/analytics {work_dir}/screenshot-analytics.png\n"
                "6. Aim for 3-5 screenshots covering the main features/views of the app\n"
                "7. If port 3000 doesn't work, check package.json for the correct port\n"
                "8. If the app has no dev server, try `npx serve . -l 3000 &` to serve static files\n"
                "Save all screenshots as PNG files in the current directory."
            ),
            model=model,
            stage_label="screenshots",
            raise_on_error=False,
            work_dir=work_dir,
            continue_session=True,
        )
        await self._collect_screenshots(task_id, work_dir=work_dir, user_id=user_id)
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await self._deactivate_squad(task_id, user_id)
        await svc.set_status(task_id, "completed")
        logger.info("Mockup pipeline COMPLETED for task %s", task_id)

    async def _run_sequential_pipeline(self, task_id: str, user_id: str) -> None:
        """Sequential pipeline: init → skills → implement-foundation → implement-feature-N → screenshots."""
        self._squad_enabled_tasks[task_id] = False
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

        # ── Init: workspace setup + squad ──
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        logger.info("Sequential init: task=%s, model=%s", task_id, model)
        await self._sandbox_exec(
            task_id=task_id,
            command=(
                f"cd {work_dir} && git init -q"
                " && git config user.email 'agent@sandbox'"
                " && git config user.name 'Sandbox Agent'"
                " && git commit --allow-empty -m 'init' -q"
                " && git remote add origin https://github.com/placeholder/repo.git 2>/dev/null || true"
            ),
            args=[],
            stage_label="init",
            work_dir=work_dir,
            raise_on_error=False,
        )
        await self._run_squad_stage(task_id, work_dir, spec_content, user_id)
        self._squad_enabled_tasks[task_id] = True
        await svc.set_iteration_stage_status(task_id, 0, "init", "completed")

        # ── Skills ──
        await svc.set_iteration_stage_status(task_id, 0, "skills", "running")
        n_skills = await self._install_skills_in_sandbox(
            task_id, task, work_dir, user_id=user_id,
        )
        if n_skills:
            logger.info("Installed %d user skills for task %s", n_skills, task_id)
        await svc.set_iteration_stage_status(task_id, 0, "skills", "completed")

        # ── Implement foundation ──
        await svc.set_iteration_stage_status(task_id, 0, "implement-foundation", "running")
        logger.info("Sequential foundation implement: task=%s", task_id)
        await self._sandbox_exec(
            task_id=task_id,
            prompt=foundation_prompt,
            model=model,
            stage_label="implement-foundation",
            stall_timeout=600,
            raise_on_error=False,
            work_dir=work_dir,
            agent="squad",
            autopilot=True,
        )
        await self._checkpoint(task_id, "foundation-implement", work_dir)
        await svc.set_iteration_stage_status(task_id, 0, "implement-foundation", "completed")

        # ── Implement features sequentially with --continue ──
        for idx, feat_prompt in enumerate(feature_prompts, start=1):
            stage_name = f"implement-feature-{idx}"
            await svc.set_iteration_stage_status(task_id, 0, stage_name, "running")
            logger.info("Sequential feature %d implement: task=%s", idx, task_id)
            await self._sandbox_exec(
                task_id=task_id,
                prompt=feat_prompt,
                model=model,
                stage_label=stage_name,
                stall_timeout=600,
                raise_on_error=False,
                work_dir=work_dir,
                continue_session=True,
                agent="squad",
                autopilot=True,
            )
            await self._checkpoint(task_id, f"feature-{idx}-implement", work_dir)
            await self._poll_squad_status(task_id, work_dir, user_id)
            await svc.set_iteration_stage_status(task_id, 0, stage_name, "completed")

        # ── Post-foundation hook: pick up any queued feature iterations ──
        task = await svc.get_by_id(task_id)
        if task:
            known_count = len(feature_prompts) + 1  # foundation + original features
            for it in task.iterations:
                if it.iteration_index >= known_count:
                    doc = await svc.get_raw(task_id) if hasattr(svc, 'get_raw') else None
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

        # ── Screenshots ──
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
                "4. Take screenshots of the key pages/views using Playwright CLI:\n"
                "   npx playwright screenshot --viewport-size='1280,800' "
                f"http://localhost:3000 {work_dir}/screenshot-overview.png\n"
                "5. Navigate to different routes/pages and take a screenshot of each:\n"
                "   npx playwright screenshot --viewport-size='1280,800' "
                f"http://localhost:3000/<route> {work_dir}/screenshot-<route>.png\n"
                "6. Aim for 3-5 screenshots covering the main features/views of the app\n"
                "7. If port 3000 doesn't work, check package.json for the correct port\n"
                "8. If the app has no dev server, try `npx serve . -l 3000 &` to serve static files\n"
                "Save all screenshots as PNG files in the current directory."
            ),
            model=model,
            stage_label="screenshots",
            raise_on_error=False,
            work_dir=work_dir,
            continue_session=True,
        )
        await self._collect_screenshots(task_id, work_dir=work_dir, user_id=user_id)
        await svc.set_iteration_stage_status(task_id, 0, "screenshots", "completed")

        await self._deactivate_squad(task_id, user_id)
        await svc.set_status(task_id, "completed")
        logger.info("Sequential pipeline COMPLETED for task %s", task_id)

    async def _run_slides_pipeline(self, task_id: str, user_id: str) -> None:
        """Slides pipeline: init (create-deckio) → slides (Copilot CLI + deck skills) → export (PDF)."""
        svc = self._service.with_user(user_id)
        task = await svc.get_by_id(task_id)
        if not task:
            return

        work_dir = f"/workspace/{task_id}"
        deck_name = task.title.lower().replace(" ", "-")[:30]
        model = await self._get_user_model(user_id)

        # Gather slides content and deck config from refined draft
        slides_prompt = f"Create a slide deck for: {task.title}"
        deck_config: dict = {}
        pptx_url: str | None = None
        if self._slides_service and task.slides_id:
            try:
                ss = self._slides_service.with_user(user_id)
                slides_data = await ss.get_by_id(task.slides_id)
                if slides_data:
                    # Parse deck config from refined draft
                    if slides_data.refined_draft:
                        from app.agents.slides_agent import SlidesAgent

                        deck_config = SlidesAgent.parse_deck_config(
                            slides_data.refined_draft
                        )
                        # Extract the ## Slides section as the prompt
                        import re

                        slides_match = re.search(
                            r"## Slides\s*\n(.+)",
                            slides_data.refined_draft,
                            re.DOTALL,
                        )
                        if slides_match:
                            slides_prompt = slides_match.group(1).strip()
                        else:
                            slides_prompt = slides_data.refined_draft
                    # Use model-level deck config as fallback
                    deck_config.setdefault("title", slides_data.title)
                    deck_config.setdefault("subtitle", getattr(slides_data, "subtitle", "") or "")
                    deck_config.setdefault("icon", getattr(slides_data, "icon", "") or "")
                    deck_config.setdefault("theme", getattr(slides_data, "theme", "shadcn/ui"))
                    deck_config.setdefault("appearance", getattr(slides_data, "appearance", "dark"))
                    deck_config.setdefault("palette", getattr(slides_data, "palette", "arctic"))
                    # Check for PowerPoint template
                    if slides_data.attachments:
                        pptx_files = [
                            a for a in slides_data.attachments if a.lower().endswith(".pptx")
                        ]
                        if pptx_files:
                            pptx_url = pptx_files[0]
            except Exception:
                logger.warning("Could not load slides data for task %s", task_id)

        # Defaults if no config parsed
        deck_config.setdefault("title", task.title)
        deck_config.setdefault("subtitle", "")
        deck_config.setdefault("theme", "shadcn/ui")
        deck_config.setdefault("appearance", "dark")
        deck_config.setdefault("palette", "arctic")

        # No squad theme for slides — slides use deck config (theme/palette/appearance)

        await svc.set_status(task_id, "running")

        # ── Stage 1: Init — git init + create-deckio scaffold ──
        await svc.set_iteration_stage_status(task_id, 0, "init", "running")
        try:
            # Git init first (required for Copilot CLI to detect .github skills)
            await self._sandbox_exec(
                task_id=task_id,
                command=(
                    f"rm -rf {work_dir} && mkdir -p {work_dir}"
                    f" && cd {work_dir}"
                    " && git init -q"
                    " && git config user.email 'agent@sandbox'"
                    " && git config user.name 'Sandbox Agent'"
                    " && git remote add origin https://github.com/placeholder/repo.git 2>/dev/null || true"
                ),
                args=[],
                stage_label="init-git",
                work_dir=work_dir,
                raise_on_error=False,
            )

            # Scaffold the deck project with parsed config
            cfg_title = deck_config["title"].replace("'", "\\'")
            cfg_subtitle = (deck_config.get("subtitle") or "").replace("'", "\\'")
            create_cmd = (
                f"cd {work_dir}"
                f" && npx -y create-deckio@latest {deck_name}"
                f" --title '{cfg_title}'"
                f" --subtitle '{cfg_subtitle}'"
                f" --theme {deck_config['theme']}"
                f" --appearance {deck_config['appearance']}"
                f" --palette {deck_config['palette']}"
                " --yes"
            )
            await self._sandbox_exec(
                task_id=task_id,
                command=create_cmd,
                args=[],
                stage_label="init",
                work_dir=work_dir,
                timeout=180,
            )
            # Move into the created deck directory
            work_dir = f"/workspace/{task_id}/{deck_name}"

            # Re-init git in the deck directory and commit scaffolded files
            # so Copilot CLI picks up the .github/ skills and instructions
            await self._sandbox_exec(
                task_id=task_id,
                command=(
                    f"cd {work_dir} && git init -q"
                    " && git config user.email 'agent@sandbox'"
                    " && git config user.name 'Sandbox Agent'"
                    " && git add -A"
                    " && git commit -m 'init: scaffold deck project' -q"
                    " && git remote add origin https://github.com/placeholder/repo.git 2>/dev/null || true"
                ),
                args=[],
                stage_label="init-git-commit",
                work_dir=work_dir,
                raise_on_error=False,
            )

            # create-deckio provides .github/ with skills and instructions
            # that Copilot CLI picks up automatically via git repo detection

            await svc.set_iteration_stage_status(task_id, 0, "init", "completed")
        except Exception as e:
            logger.error("Slides init failed for %s: %s", task_id, e)
            await svc.set_iteration_stage_status(
                task_id, 0, "init", "failed", error=str(e)
            )
            await svc.set_status(task_id, "failed")
            return

        # ── Stage 2: Slides — single autopilot invocation ──
        await svc.set_iteration_stage_status(task_id, 0, "slides", "running")
        try:
            # Wrap the slide content prompt with project context so Copilot CLI
            # uses the existing theme, palette, and .github skills from create-deckio
            full_slides_prompt = (
                "This is a Slidev slide deck project scaffolded with create-deckio. "
                f"The project uses theme '{deck_config.get('theme', 'shadcn/ui')}', "
                f"appearance '{deck_config.get('appearance', 'dark')}', "
                f"and color palette '{deck_config.get('palette', 'arctic')}'. "
                "Read the existing project files (especially slides.md, .github/ "
                "instructions, and the theme config) before making changes. "
                "Build on top of the existing scaffolded project — do NOT replace "
                "the theme or configuration. Edit slides.md to create the slides.\n\n"
                f"{slides_prompt}"
            )
            await self._sandbox_exec(
                task_id=task_id,
                prompt=full_slides_prompt,
                model=model,
                stage_label="slides",
                work_dir=work_dir,
                timeout=2400,
                stall_timeout=600,
                autopilot=True,
            )

            # PowerPoint template porting (if .pptx attached)
            if pptx_url:
                _buf_append(task_id, {
                    "type": "stage",
                    "data": f"Porting PowerPoint template: {pptx_url.split('/')[-1]}",
                    "ts": __import__("time").time(),
                })
                await self._sandbox_exec(
                    task_id=task_id,
                    prompt=f"/deck-port-powerpoint {pptx_url}",
                    model=model,
                    stage_label="pptx-port",
                    work_dir=work_dir,
                    timeout=180,
                    stall_timeout=120,
                    continue_session=True,
                    autopilot=True,
                )

            await svc.set_iteration_stage_status(task_id, 0, "slides", "completed")
        except Exception as e:
            logger.error("Slides generation failed for %s: %s", task_id, e)
            await svc.set_iteration_stage_status(
                task_id, 0, "slides", "failed", error=str(e)
            )
            await svc.set_status(task_id, "failed")
            return

        # ── Stage 3: Export — PDF generation ──
        await svc.set_iteration_stage_status(task_id, 0, "export", "running")
        try:
            # Run npm install + slidev export directly (no Copilot CLI needed)
            await self._sandbox_exec(
                task_id=task_id,
                command=(
                    f"cd {work_dir}"
                    " && npm install --silent 2>&1"
                    " && npx slidev export --output slides.pdf --timeout 60000 2>&1"
                    " || npx slidev export --output slides.pdf 2>&1"
                ),
                args=[],
                stage_label="export",
                work_dir=work_dir,
                timeout=300,
                raise_on_error=False,
            )

            # Upload PDF to blob storage
            pdf_url = await self._upload_slides_pdf(task_id, work_dir, user_id)
            if pdf_url:
                await svc.set_export_artifacts(task_id, {"pdfUrl": pdf_url})
                logger.info("Slides PDF uploaded for task %s: %s", task_id, pdf_url)

            await svc.set_iteration_stage_status(task_id, 0, "export", "completed")
        except Exception as e:
            logger.error("Slides export failed for %s: %s", task_id, e)
            await svc.set_iteration_stage_status(
                task_id, 0, "export", "failed", error=str(e)
            )
            await svc.set_status(task_id, "failed")
            return

        await svc.set_status(task_id, "completed")
        logger.info("Slides pipeline COMPLETED for task %s", task_id)

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
        if task.mode not in ("sequential", "openspec"):
            return {"error": "Only sequential mode supports incremental features", "extended": False, "pipeline_triggered": False}

        # Determine foundation status
        foundation_completed = False
        if task.iterations:
            foundation = task.iterations[0]
            foundation_completed = all(
                s.status == "completed" for s in foundation.stages
                if s.name in ("init", "propose", "apply")
            )

        # Create the new iteration
        iteration_data = _default_iteration(0, f"Feature: {feature_name}", spec_id, mode="sequential")
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
            # Implement feature with --continue
            stage_name = f"implement-feature-{iteration_index}"
            await svc.set_iteration_stage_status(task_id, iteration_index, stage_name, "running")
            logger.info("Incremental feature implement: task=%s, iter=%d", task_id, iteration_index)
            await self._sandbox_exec(
                task_id=task_id,
                prompt=propose_instruction,
                model=model,
                stage_label=f"feature-{iteration_index}-implement",
                work_dir=work_dir,
                continue_session=True,
                agent="squad",
                autopilot=True,
            )
            await svc.set_iteration_stage_status(task_id, iteration_index, stage_name, "completed")

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
                continue_session=True,
            )
            await self._collect_screenshots(task_id, work_dir=work_dir, user_id=user_id)
            await svc.set_iteration_stage_status(task_id, iteration_index, "screenshots", "completed")

            # Check if all iterations are done
            task = await svc.get_by_id(task_id)
            if task:
                all_done = all(
                    all(s.status == "completed" for s in it.stages
                        if s.name.startswith("implement"))
                    for it in task.iterations
                )
                if all_done:
                    await self._deactivate_squad(task_id, user_id)
                    await svc.set_status(task_id, "completed")

            logger.info("Incremental feature pipeline COMPLETED: task=%s, iter=%d", task_id, iteration_index)

        except Exception as e:
            logger.exception("Incremental feature pipeline FAILED: task=%s, iter=%d", task_id, iteration_index)
            try:
                stage_name = f"implement-feature-{iteration_index}"
                await svc.set_iteration_stage_status(
                    task_id, iteration_index, stage_name, "failed", error=str(e)
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
        stall_timeout: float = 600,
        raise_on_error: bool = True,
        work_dir: str = "/workspace",
        continue_session: bool = False,
        agent: str | None = None,
        autopilot: bool = False,
    ) -> str:
        """Submit a task to the sandbox and stream output via SSE.

        Streams real-time output into the pipeline buffer for the terminal view.
        Detects CLI questions and auto-answers them using the model.
        Returns combined stdout output.

        Args:
            stall_timeout: Seconds of silence (no stdout) before considering the
                task stalled and killing it. Default 180s (3 minutes).
            continue_session: If True, adds --continue flag to Copilot CLI to
                resume the previous session and maintain context across stages.
            agent: If set (e.g. "squad"), adds --agent flag to Copilot CLI.
        """
        payload: dict = {"workDir": work_dir}
        if prompt:
            payload["prompt"] = prompt
            payload["model"] = model
            if continue_session:
                payload["continueSession"] = True
            if agent:
                payload["agent"] = agent
            if autopilot:
                payload["autopilot"] = True
        elif command:
            payload["command"] = command
            payload["args"] = args or []
        else:
            raise ValueError("prompt or command is required")

        # Inject per-user GitHub PAT if available
        gh_token = getattr(self, "_current_gh_token", None)
        if gh_token:
            payload["ghToken"] = gh_token

        log_preview = prompt[:120] if prompt else f"{command} {args}"
        logger.info("Sandbox exec [%s]: %s", stage_label, log_preview)

        # Ensure pipeline output buffer exists
        if task_id and task_id not in _pipeline_outputs:
            _pipeline_outputs[task_id] = []
        output_buf = _pipeline_outputs.get(task_id, [])

        logger.info(
            "[SANDBOX-DIAG] Starting sandbox task stage=%s task_id=%s "
            "sandbox_url=%s buf_id=%s",
            stage_label, task_id, SANDBOX_URL, id(output_buf),
        )

        # Emit stage marker
        if task_id:
            _buf_append(task_id, {
                "type": "stage", "data": f"── {stage_label} ──", "ts": time.time()
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{SANDBOX_URL}/tasks", json=payload)
            resp.raise_for_status()
            task_data = resp.json()
            sandbox_task_id = task_data["id"]

        # Track active sandbox task for cleanup on dev-task deletion
        if task_id:
            _active_sandbox_tasks[task_id] = sandbox_task_id

        logger.info(
            "[SANDBOX-DIAG] Task created sandbox_task=%s stage=%s, "
            "connecting SSE to %s/tasks/%s/stream",
            sandbox_task_id, stage_label, SANDBOX_URL, sandbox_task_id,
        )

        # Stream output via SSE
        # Use per-line async timeout to detect silently dropped connections
        # (Azure Container Apps proxy may kill idle connections without TCP RST)
        SSE_LINE_TIMEOUT = 60  # no line (incl. keepalive) for 60s → dead connection
        start = time.monotonic()
        last_output_time = time.monotonic()  # tracks meaningful stdout/stderr
        last_any_traffic = time.monotonic()  # tracks any SSE traffic (incl keepalive)
        exit_code = -1
        output_lines: list[str] = []
        accumulated_text = ""
        line_count = 0

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, read=None),
            ) as client:
                async with client.stream(
                    "GET", f"{SANDBOX_URL}/tasks/{sandbox_task_id}/stream"
                ) as sse_resp:
                    logger.info(
                        "[SANDBOX-DIAG] SSE connected status=%d stage=%s",
                        sse_resp.status_code, stage_label,
                    )
                    lines_iter = sse_resp.aiter_lines()
                    while True:
                        try:
                            raw_line = await asyncio.wait_for(
                                lines_iter.__anext__(), timeout=SSE_LINE_TIMEOUT,
                            )
                        except StopAsyncIteration:
                            break
                        except TimeoutError:
                            logger.warning(
                                "SSE line timeout (%ds, no data) [%s], "
                                "falling back to polling",
                                SSE_LINE_TIMEOUT, stage_label,
                            )
                            raise

                        now = time.monotonic()
                        if now - start > timeout:
                            await self._kill_sandbox_task(sandbox_task_id, stage_label)
                            raise RuntimeError(
                                f"Sandbox task timed out: {stage_label}"
                            )
                        # Stall detection: no meaningful stdout/stderr for too long
                        # (keepalives don't count — they just prove the connection is alive)
                        if now - last_output_time > stall_timeout:
                            await self._kill_sandbox_task(sandbox_task_id, stage_label)
                            raise RuntimeError(
                                f"Sandbox task stalled (no output for "
                                f"{stall_timeout:.0f}s): {stage_label}"
                            )

                        if not raw_line.startswith("data: "):
                            # Keepalive/comment — proves connection alive but NOT real output
                            if raw_line.strip():
                                last_any_traffic = now
                            continue

                        line_count += 1
                        if line_count <= 3 or line_count % 50 == 0:
                            logger.info(
                                "[SANDBOX-DIAG] SSE line #%d stage=%s buf=%d",
                                line_count, stage_label, len(output_buf),
                            )

                        try:
                            entry = json.loads(raw_line[6:])
                        except json.JSONDecodeError:
                            continue

                        entry_type = entry.get("type", "")

                        # Forward to pipeline buffer for terminal view
                        # (skip exit events — the pipeline emits its own on completion)
                        if task_id and entry_type != "exit":
                            _buf_append(task_id, entry)

                        if entry_type == "stdout":
                            data = entry.get("data", "")
                            output_lines.append(data)
                            accumulated_text += data
                            if data.strip():
                                last_output_time = now

                            # Real-time premium request parsing from stream
                            if task_id and prompt and data.strip():
                                premium_line = re.search(
                                    r"Total usage est:\s+([\d.]+)\s+Premium request",
                                    data.strip(),
                                )
                                if premium_line:
                                    parsed_premium = float(premium_line.group(1))
                                    # Round up fractional requests to whole number
                                    rounded = int(parsed_premium) if parsed_premium == int(parsed_premium) else int(parsed_premium) + 1
                                    if rounded > 0:
                                        try:
                                            pr_svc = (
                                                self._service.with_user(self._current_user_id)
                                                if hasattr(self, "_current_user_id")
                                                and self._current_user_id
                                                else self._service
                                            )
                                            if hasattr(pr_svc, "add_premium_requests"):
                                                await pr_svc.add_premium_requests(
                                                    task_id, rounded,
                                                )
                                        except Exception:
                                            pass

                            # Parse squad agent activity from stream
                            if task_id and data.strip():
                                squad_match = re.search(
                                    r"(?:●\s+\S+\s+)?(?:\S+\s+)?([A-Z][a-z]+):\s+(.+)",
                                    data.strip(),
                                )
                                if squad_match:
                                    agent_name = squad_match.group(1)
                                    agent_task = squad_match.group(2).strip()
                                    # Known squad member names from all themes
                                    known_names = {
                                        # Aliens (default)
                                        "Hicks", "Ripley", "Dallas", "Lambert", "Parker", "Scribe",
                                        # Star Wars
                                        "Obi-Wan", "Leia", "Han", "Chewie", "R2-D2", "C-3PO",
                                        # LOTR
                                        "Aragorn", "Legolas", "Gimli", "Gandalf", "Samwise", "Frodo",
                                        # Matrix
                                        "Morpheus", "Trinity", "Neo", "Tank", "Switch", "Oracle",
                                        # Marvel
                                        "Fury", "Stark", "Banner", "Romanoff", "Thor", "Jarvis",
                                    }
                                    if agent_name in known_names:
                                        try:
                                            svc = (
                                                self._service.with_user(self._current_user_id)
                                                if hasattr(self, "_current_user_id")
                                                and self._current_user_id
                                                else self._service
                                            )
                                            t = await svc.get_by_id(task_id)
                                            if t and t.squad:
                                                for m in t.squad.team_members:
                                                    if m.name == agent_name:
                                                        m.status = "working"
                                                        m.activity = agent_task
                                                        break
                                                await svc.set_squad(
                                                    task_id,
                                                    {
                                                        "teamMembers": [
                                                            m.model_dump(by_alias=True)
                                                            for m in t.squad.team_members
                                                        ]
                                                    },
                                                )
                                        except Exception:
                                            pass  # Non-fatal: squad update is best-effort

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

        except (TimeoutError, httpx.HTTPError) as e:
            logger.warning(
                "[SANDBOX-DIAG] SSE stream error [%s] type=%s, "
                "lines_received=%d buf_size=%d, falling back to polling: %s",
                stage_label, type(e).__name__, line_count, len(output_buf), e,
            )
            # Fallback: poll for completion
            exit_code = await self._poll_until_done(
                sandbox_task_id, stage_label, timeout - (time.monotonic() - start),
                output_lines, output_buf, task_id,
            )

        combined = "".join(output_lines)

        # Clear active sandbox task tracking
        _active_sandbox_tasks.pop(task_id, None)
        logger.info(
            "[SANDBOX-DIAG] Sandbox exec [%s] exit=%d chars=%d "
            "lines=%d buf_size=%d elapsed=%.0fs",
            stage_label, exit_code, len(combined),
            line_count, len(output_buf), time.monotonic() - start,
        )

        # Emit a per-stage exit marker so SSE consumers see the stage ended.
        # The pipeline-level exit event is emitted in run_pipeline's finally block,
        # but individual stage completion must also be signalled — especially when
        # the SSE stream fell back to polling and the original exit event was lost.
        if task_id and task_id in _pipeline_outputs:
            _buf_append(task_id, {
                "type": "stage_exit",
                "stage": stage_label,
                "code": exit_code,
                "ts": time.time(),
            })

        if exit_code != 0 and raise_on_error:
            raise RuntimeError(
                f"Sandbox task [{stage_label}] failed with exit code {exit_code}"
            )

        return combined

    async def _kill_sandbox_task(self, sandbox_task_id: str, stage_label: str) -> None:
        """Kill a running sandbox task process to free resources on timeout/stall."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{SANDBOX_URL}/tasks/{sandbox_task_id}")
                logger.info(
                    "[SANDBOX-DIAG] Kill task %s [%s]: %s",
                    sandbox_task_id, stage_label, resp.json(),
                )
        except Exception as exc:
            logger.warning("Failed to kill sandbox task %s: %s", sandbox_task_id, exc)

    async def _poll_squad_status(
        self, task_id: str, work_dir: str, user_id: str,
    ) -> None:
        """Poll squad status and update member activity in the service."""
        try:
            raw = await self._sandbox_exec(
                task_id=task_id,
                command=f"test -f {work_dir}/.squad/config.json && squad status --json 2>/dev/null || echo '[]'",
                args=[],
                stage_label="squad-status",
                work_dir=work_dir,
                timeout=15,
                raise_on_error=False,
            )
            if not raw.strip() or raw.strip() == "[]":
                return
            status_data = json.loads(raw.strip())
            if not isinstance(status_data, list):
                return
            svc = self._service.with_user(user_id)
            task = await svc.get_by_id(task_id)
            if not task or not task.squad:
                return
            active_names = {m.get("name", "") for m in status_data if m.get("active")}
            updated_members = []
            for m in task.squad.team_members:
                if m.name in active_names:
                    m.status = "working"
                elif m.status == "working":
                    m.status = "done"
                updated_members.append(m)
            await svc.set_squad(task_id, {"teamMembers": [m.model_dump(by_alias=True) for m in updated_members]})
        except Exception as exc:
            logger.debug("squad status poll failed (non-fatal): %s", exc)

    async def _deactivate_squad(self, task_id: str, user_id: str) -> None:
        """Mark all squad members as done when pipeline completes."""
        try:
            svc = self._service.with_user(user_id)
            task = await svc.get_by_id(task_id)
            if not task or not task.squad or not task.squad.team_members:
                return
            for m in task.squad.team_members:
                m.status = "done"
                m.activity = ""
            await svc.set_squad(
                task_id,
                {"teamMembers": [m.model_dump(by_alias=True) for m in task.squad.team_members]},
            )
        except Exception as exc:
            logger.debug("Failed to deactivate squad for task %s: %s", task_id, exc)

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
                command=(
                    f"cd {work_dir} && git add -A && "
                    f'git diff --cached --quiet || git commit -m "checkpoint: {label}"'
                ),
                args=[],
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
                command=f"find {work_dir}/openspec/changes -name tasks.md 2>/dev/null | head -1",
                args=[],
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
        _buf_append(task_id, {
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
                        timestamp=datetime.now(UTC).isoformat(),
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
        consecutive_404s = 0
        async with httpx.AsyncClient(timeout=15.0) as client:
            while time.monotonic() - start < remaining_timeout:
                await asyncio.sleep(3)
                try:
                    resp = await client.get(
                        f"{SANDBOX_URL}/tasks/{sandbox_task_id}/status"
                    )
                    if resp.status_code == 404:
                        consecutive_404s += 1
                        logger.warning(
                            "Sandbox task %s not found (attempt %d) [%s]",
                            sandbox_task_id, consecutive_404s, stage_label,
                        )
                        # Task gone — sandbox likely restarted, treat as failure
                        if consecutive_404s >= 3:
                            logger.error(
                                "Sandbox task %s gone after %d 404s — "
                                "sandbox likely restarted [%s]",
                                sandbox_task_id, consecutive_404s, stage_label,
                            )
                            return 1  # Non-zero exit = failure
                        continue
                    resp.raise_for_status()
                    status = resp.json()
                    consecutive_404s = 0  # Reset on success
                except httpx.HTTPStatusError:
                    continue
                except Exception:
                    continue

                if status.get("done"):
                    for entry in status.get("recentOutput", []):
                        if entry.get("type") == "stdout":
                            data = entry.get("data", "")
                            output_lines.append(data)
                        if task_id:
                            _buf_append(task_id, entry)
                    return status.get("exitCode", -1)

        raise RuntimeError(f"Sandbox task timed out: {stage_label}")

    async def _collect_screenshots(
        self, task_id: str, work_dir: str = "/workspace", user_id: str | None = None
    ) -> None:
        """Fetch screenshot PNGs from the sandbox workspace and store as artifacts."""
        svc = self._service.with_user(user_id) if user_id else self._service
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                files: list[str] = []
                # Search with multiple glob patterns (screenshots, slides, any png)
                for pattern in ("screenshot*.png", "slide-*.png", "slide_*.png", "*.png"):
                    resp = await client.get(
                        f"{SANDBOX_URL}/files",
                        params={"glob": pattern, "dir": work_dir},
                    )
                    resp.raise_for_status()
                    files = resp.json().get("files", [])
                    if files:
                        break
                logger.info("Found %d screenshot files in sandbox for task %s", len(files), task_id)

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

    async def _upload_slides_pdf(
        self, task_id: str, work_dir: str, user_id: str | None = None
    ) -> str | None:
        """Fetch the exported PDF from sandbox and upload to Azure Blob Storage."""
        storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        if not storage_account:
            logger.warning("No AZURE_STORAGE_ACCOUNT_NAME — skipping PDF upload")
            return None

        try:
            # Find the PDF file in the sandbox workspace
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{SANDBOX_URL}/files",
                    params={"glob": "*.pdf", "dir": work_dir},
                )
                resp.raise_for_status()
                files = resp.json().get("files", [])

            if not files:
                logger.warning("No PDF file found in sandbox for task %s", task_id)
                return None

            pdf_path = files[0]
            rel = pdf_path.replace("/workspace/", "", 1)

            # Download PDF binary from sandbox
            async with httpx.AsyncClient(timeout=60.0) as client:
                fresp = await client.get(
                    f"{SANDBOX_URL}/files/{rel}",
                    params={"raw": "true"},
                )
                fresp.raise_for_status()
                pdf_bytes = fresp.content

            if len(pdf_bytes) < 100:
                logger.warning("PDF file too small (%d bytes), skipping upload", len(pdf_bytes))
                return None

            # Upload to blob storage
            from azure.identity.aio import DefaultAzureCredential
            from azure.storage.blob.aio import BlobServiceClient

            credential = DefaultAzureCredential()
            blob_service = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential,
            )
            blob_name = f"exports/{task_id}/slides.pdf"
            async with blob_service:
                container = blob_service.get_container_client("exports")
                try:
                    await container.create_container()
                except Exception:
                    pass  # Already exists
                blob_client = container.get_blob_client(blob_name)
                from azure.storage.blob import ContentSettings
                await blob_client.upload_blob(
                    pdf_bytes,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/pdf"),
                )

            pdf_url = f"https://{storage_account}.blob.core.windows.net/exports/{blob_name}"
            logger.info("Uploaded slides PDF: %s (%d bytes)", pdf_url, len(pdf_bytes))
            return pdf_url

        except Exception as e:
            logger.error("Failed to upload slides PDF for task %s: %s", task_id, e)
            return None

    # ── Shared pipeline stages ──────────────────────────────────────

    async def _auto_attach_skills(self, task_id: str, title: str, spec_id: str | None = None, user_id: str | None = None) -> None:
        """Auto-suggest and attach relevant skills to a task based on title + spec content."""
        if not self._cosmos_skills:
            return
        content = title
        if spec_id and self._spec_service:
            spec_svc = self._spec_service.with_user(user_id) if user_id else self._spec_service
            spec = await spec_svc.get_by_id(spec_id)
            if spec:
                content = f"{spec.title} {spec.content} {title}"
        svc = self._cosmos_skills.with_user(user_id) if user_id else self._cosmos_skills
        activated = await svc.list_activated()
        suggested = self._skills_service.suggest_skills_for_content(content, activated)
        # Fallback: if no keyword match, include all activated skills
        if not suggested:
            suggested = [s["name"] for s in activated]
        if suggested:
            await self._service.set_skill_ids(task_id, suggested)
            logger.info("Auto-attached skills %s to task %s", suggested, task_id)

    # ── Squad integration ─────────────────────────────────────────────

    def _generate_squad_team(self, spec_content: str, theme: str = "") -> list[dict]:
        """Parse spec content for tech keywords and return squad team roster.

        If a theme is provided (e.g. "Star Wars"), use themed character names.
        """
        content_lower = spec_content.lower() if spec_content else ""

        # Theme-based name sets
        theme_names = self._get_themed_names(theme)

        team: list[dict] = []

        # Always-present roles
        team.append({"name": theme_names["lead"], "role": "Lead", "expertise": "Architecture, code review, scope", "status": "idle"})

        # Dynamic roles based on tech stack detection
        frontend_kw = ["react", "next.js", "nextjs", "vue", "angular", "svelte", "tailwind", "css", "html", "frontend", "ui component"]
        backend_kw = ["python", "fastapi", "flask", "django", "express", "node.js", "api", "endpoint", "backend", "server"]
        test_kw = ["test", "jest", "pytest", "playwright", "cypress", "testing", "spec"]
        devops_kw = ["docker", "kubernetes", "bicep", "terraform", "ci/cd", "pipeline", "deploy", "infrastructure"]

        has_frontend = any(kw in content_lower for kw in frontend_kw)
        has_backend = any(kw in content_lower for kw in backend_kw)
        has_testing = any(kw in content_lower for kw in test_kw)
        has_devops = any(kw in content_lower for kw in devops_kw)

        if has_frontend:
            team.append({"name": theme_names["frontend"], "role": "Frontend Dev", "expertise": "React, TypeScript, UI", "status": "idle"})
        if has_backend:
            team.append({"name": theme_names["backend"], "role": "Backend Dev", "expertise": "Python, FastAPI, APIs", "status": "idle"})
        if has_testing or has_frontend or has_backend:
            team.append({"name": theme_names["tester"], "role": "Tester", "expertise": "Jest, Playwright, integration tests", "status": "idle"})
        if has_devops:
            team.append({"name": theme_names["devops"], "role": "DevOps", "expertise": "Docker, CI/CD, infrastructure", "status": "idle"})

        # If nothing detected, add a generic Developer
        if len(team) == 1:
            team.append({"name": theme_names["backend"], "role": "Developer", "expertise": "Full-stack development", "status": "idle"})
            team.append({"name": theme_names["tester"], "role": "Tester", "expertise": "Testing, quality assurance", "status": "idle"})

        # Scribe is always last (silent role)
        team.append({"name": theme_names["scribe"], "role": "Scribe", "expertise": "Memory, decisions, session logs", "status": "idle"})

        return team

    @staticmethod
    def _get_themed_names(theme: str) -> dict[str, str]:
        """Return role→name mapping based on the squad theme."""
        t = theme.strip().lower() if theme else ""
        if "star wars" in t:
            return {
                "lead": "Obi-Wan", "frontend": "Leia", "backend": "Han",
                "tester": "Chewie", "devops": "R2-D2", "scribe": "C-3PO",
            }
        if "lord of the rings" in t or "lotr" in t:
            return {
                "lead": "Aragorn", "frontend": "Legolas", "backend": "Gimli",
                "tester": "Gandalf", "devops": "Samwise", "scribe": "Frodo",
            }
        if "matrix" in t:
            return {
                "lead": "Morpheus", "frontend": "Trinity", "backend": "Neo",
                "tester": "Tank", "devops": "Switch", "scribe": "Oracle",
            }
        if "marvel" in t:
            return {
                "lead": "Fury", "frontend": "Stark", "backend": "Banner",
                "tester": "Romanoff", "devops": "Thor", "scribe": "Jarvis",
            }
        # Default: Aliens theme
        return {
            "lead": "Hicks", "frontend": "Ripley", "backend": "Dallas",
            "tester": "Lambert", "devops": "Parker", "scribe": "Scribe",
        }

    def _generate_squad_files(self, team: list[dict], spec_content: str) -> dict[str, str]:
        """Generate .squad/ config files from team and spec content."""
        # config.json — must be valid JSON for squad-pr validation
        config_json = json.dumps({
            "teamRoot": ".",
            "team": "team.md",
            "routing": "routing.md",
            "directives": "directives.md",
        }, indent=2) + "\n"

        # team.md — squad-pr expects "## Members" header
        team_lines = ["## Members\n"]
        role_emojis = {
            "Lead": "🏗️", "Frontend Dev": "⚛️", "Backend Dev": "🔧",
            "Tester": "🧪", "DevOps": "🚀", "Developer": "💻", "Scribe": "📋",
        }
        for m in team:
            emoji = role_emojis.get(m["role"], "👤")
            silent = " (silent)" if m["role"] == "Scribe" else ""
            team_lines.append(f"{emoji}  {m['name']}  — {m['role']}{silent}  {m['expertise']}")
        team_md = "\n".join(team_lines) + "\n"

        # routing.md — map work to roles
        routing_lines = ["# Routing Rules\n"]
        for m in team:
            if m["role"] == "Frontend Dev":
                routing_lines.append(f"**Frontend changes** → {m['name']}")
                routing_lines.append(f"**UI/UX work** → {m['name']}")
            elif m["role"] == "Backend Dev":
                routing_lines.append(f"**Backend API work** → {m['name']}")
                routing_lines.append(f"**Database changes** → {m['name']}")
            elif m["role"] == "Tester":
                routing_lines.append(f"**Test writing** → {m['name']}")
            elif m["role"] == "DevOps":
                routing_lines.append(f"**Infrastructure** → {m['name']}")
            elif m["role"] == "Lead":
                routing_lines.append(f"**Architecture decisions** → {m['name']}")
        routing_md = "\n".join(routing_lines) + "\n"

        # directives.md — extract conventions from spec
        directives_lines = ["# Team Directives\n"]
        directives_lines.append("- Follow the project spec for all implementation decisions")
        directives_lines.append("- Keep changes minimal and focused on the task at hand")
        directives_lines.append("- Write tests alongside implementation when applicable")
        if "typescript" in (spec_content or "").lower():
            directives_lines.append("- Use TypeScript strict mode")
        if "python" in (spec_content or "").lower():
            directives_lines.append("- Follow PEP 8 and use type hints")
        directives_md = "\n".join(directives_lines) + "\n"

        return {
            ".squad/config.json": config_json,
            ".squad/team.md": team_md,
            ".squad/routing.md": routing_md,
            ".squad/directives.md": directives_md,
        }

    async def _run_squad_stage(
        self, task_id: str, work_dir: str, spec_content: str, user_id: str,
    ) -> None:
        """Initialize squad-pr in the workspace and hire agents based on spec."""
        svc = self._service.with_user(user_id)
        logger.info("Squad stage: task=%s", task_id)

        # Step 1: squad init
        if task_id in _pipeline_outputs:
            _buf_append(task_id, {
                "type": "stdout", "data": "── Initializing Squad ──\n", "stage": "squad",
            })
        try:
            await self._sandbox_exec(
                task_id=task_id,
                command="squad",
                args=["init"],
                stage_label="squad-init",
                work_dir=work_dir,
                timeout=60,
                raise_on_error=False,
            )
        except Exception as exc:
            logger.warning("squad init failed (non-fatal): %s", exc)

        # Ensure casting/registry.json exists for squad-pr validation
        try:
            await self._sandbox_exec(
                task_id=task_id,
                command=f"mkdir -p {work_dir}/.squad/casting && echo '[]' > {work_dir}/.squad/casting/registry.json",
                args=[],
                stage_label="squad-registry",
                work_dir=work_dir,
                timeout=15,
                raise_on_error=False,
            )
        except Exception as exc:
            logger.warning("squad registry init failed (non-fatal): %s", exc)

        # Step 2: Generate team from spec with user's theme preference
        theme = _DEFAULT_SQUAD_THEME
        if self._profile_service:
            try:
                theme = await self._profile_service.get_squad_theme(user_id)
            except Exception:
                pass
        team = self._generate_squad_team(spec_content, theme=theme or "")
        squad_files = self._generate_squad_files(team, spec_content)

        # Step 3: Write .squad/ config files
        for file_path, content in squad_files.items():
            full_path = f"{work_dir}/{file_path}"
            escaped = content.replace("'", "'\\''")
            try:
                await self._sandbox_exec(
                    task_id=task_id,
                    command=f"mkdir -p $(dirname {full_path}) && printf '%s' '{escaped}' > {full_path}",
                    args=[],
                    stage_label="squad-config",
                    work_dir=work_dir,
                    timeout=15,
                    raise_on_error=False,
                )
            except Exception as exc:
                logger.warning("Failed to write %s: %s", file_path, exc)

        # Step 4: Hire each agent
        for member in team:
            if task_id in _pipeline_outputs:
                _buf_append(task_id, {
                    "type": "stdout",
                    "data": f"  Hiring {member['name']} as {member['role']}...\n",
                    "stage": "squad",
                })
            try:
                await self._sandbox_exec(
                    task_id=task_id,
                    command="squad",
                    args=["hire", "--name", member["name"], "--role", member["role"]],
                    stage_label=f"squad-hire-{member['name'].lower()}",
                    work_dir=work_dir,
                    timeout=30,
                    raise_on_error=False,
                )
            except Exception as exc:
                logger.warning("squad hire %s failed: %s", member["name"], exc)

        # Step 5: squad doctor (non-fatal)
        try:
            await self._sandbox_exec(
                task_id=task_id,
                command="squad",
                args=["doctor"],
                stage_label="squad-doctor",
                work_dir=work_dir,
                timeout=30,
                raise_on_error=False,
            )
        except Exception as exc:
            logger.warning("squad doctor failed (non-fatal): %s", exc)

        # Step 6: Store squad metadata
        squad_data = {"teamMembers": team}
        await svc.set_squad(task_id, squad_data)

        if task_id in _pipeline_outputs:
            names = ", ".join(f"{m['name']} ({m['role']})" for m in team)
            _buf_append(task_id, {
                "type": "stdout",
                "data": f"── Squad ready: {names} ──\n",
                "stage": "squad",
            })
        logger.info("Squad stage complete: %d members for task %s", len(team), task_id)

    async def _install_skills_in_sandbox(
        self, task_id: str, task, work_dir: str, user_id: str | None = None,
    ) -> int:
        """Sync activated skills from blob storage into the sandbox.

        All skills (local and marketplace) are pre-uploaded to blob storage.
        This method runs a quick blob sync to ensure the sandbox has the latest
        files, handling the case where skills were activated after container start.
        Returns the number of skills synced.
        """
        if not self._cosmos_skills or not task.skill_ids:
            return 0

        svc = self._cosmos_skills.with_user(user_id) if user_id else self._cosmos_skills
        npx_map = await svc.get_npx_commands(task.skill_ids)
        if not npx_map:
            return 0

        skill_names = list(npx_map.keys())
        if task_id in _pipeline_outputs:
            _buf_append(task_id, {
                "type": "stdout",
                "data": f"── Syncing {len(skill_names)} skill(s) from blob storage ──\n",
                "stage": "install-skills",
            })

        # Single blob sync command for all skills — fast compared to npx installs
        skills_list = " ".join(skill_names)
        sync_cmd = (
            'SKILLS_DIR="/home/agent/.copilot/skills" && '
            f'for SKILL in {skills_list}; do '
            'if [ ! -f "$SKILLS_DIR/$SKILL/SKILL.md" ]; then '
            'BLOBS=$(az storage blob list --account-name "$AZURE_STORAGE_ACCOUNT_NAME" '
            '--container-name skills --prefix "$SKILL/" --auth-mode login '
            '--query "[].name" -o tsv 2>/dev/null); '
            'if [ -n "$BLOBS" ]; then '
            'while IFS= read -r blob; do '
            '[ -z "$blob" ] && continue; '
            'dest="$SKILLS_DIR/$blob"; '
            'mkdir -p "$(dirname "$dest")"; '
            'az storage blob download --account-name "$AZURE_STORAGE_ACCOUNT_NAME" '
            '--container-name skills --name "$blob" --file "$dest" '
            '--auth-mode login --no-progress 2>/dev/null; '
            'done <<< "$BLOBS"; '
            'echo "  ✓ $SKILL synced from blob"; '
            'else echo "  ⚠ $SKILL not found in blob storage"; fi; '
            'else echo "  ✓ $SKILL already present"; fi; '
            'done'
        )
        try:
            await self._sandbox_exec(
                task_id=task_id,
                command=sync_cmd,
                args=[],
                stage_label="sync-skills",
                work_dir=work_dir,
                timeout=60,
                raise_on_error=False,
            )
        except Exception as exc:
            logger.warning("Blob skill sync failed: %s", exc)

        installed = len(skill_names)
        if installed and task_id in _pipeline_outputs:
            _buf_append(task_id, {
                "type": "stdout",
                "data": f"Activated {installed} skills in workspace\n",
                "stage": "install-skills",
            })

        # ── Verify all skills with a single CLI prompt ───────────────
        await self._verify_skills_in_sandbox(task_id, work_dir)

        return installed

    async def _verify_skills_in_sandbox(
        self, task_id: str, work_dir: str,
    ) -> None:
        """Reload skills from disk, then verify via 'What skills do you have?'

        Two-step: first triggers a reload so the CLI picks up any newly
        installed or blob-synced skills, then asks what it sees.
        Uses claude-haiku-4.5 (cheap) to minimize premium request cost.
        """
        if task_id in _pipeline_outputs:
            _buf_append(task_id, {
                "type": "stdout",
                "data": "── verify-skills ──\n",
                "stage": "verify-skills",
            })

        try:
            await self._sandbox_exec(
                task_id=task_id,
                prompt="Reload your skills from disk, then tell me: What skills do you have?",
                model="claude-haiku-4.5",
                stage_label="verify-skills",
                work_dir=work_dir,
                timeout=60,
                stall_timeout=30,
                raise_on_error=False,
            )
        except Exception as exc:
            logger.warning("CLI skill verification failed: %s", exc)
            if task_id in _pipeline_outputs:
                _buf_append(task_id, {
                    "type": "stderr",
                    "data": f"Skill verification error: {exc}\n",
                    "stage": "verify-skills",
                })

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
