## Context

The slides dev-task pipeline builds Slidev presentation decks inside ACI sandbox containers. The current implementation has three stages (`init`, `skills`, `slides`) but suffers from:

1. **Broken live preview**: The backend `start_live` route tries to start `npx slidev --port 3333` on demand, but this races with sandbox lifecycle and often fails with "Dev server not reachable on port 3333".
2. **Missing run stage**: There is no pipeline stage that installs dependencies and starts the dev server. The dev server startup is handled outside the pipeline in `dev.py` routes, disconnected from the pipeline flow.
3. **Unnecessary skills stage**: Skills sync is a prerequisite for Copilot CLI, not a user-visible pipeline stage. It should be part of init.
4. **Current Copilot CLI invocation** uses `_sandbox_exec()` which wraps prompts in `copilot -p <prompt>`. The desired approach is `copilot --autopilot --yolo` running interactively in the deck directory.

Key files: `backend/app/agents/dev_agent.py` (pipeline), `backend/app/services/dev_service.py` (stage names), `backend/app/routes/dev.py` (live preview routes), `sandbox/server.js` (proxy).

## Goals / Non-Goals

**Goals:**
- Restructure pipeline to `init → slides → run` with clear separation of concerns
- Make live preview work reliably by starting the dev server as a pipeline stage
- Use `copilot --autopilot --yolo` for slide generation (interactive session in deck dir)
- Support PowerPoint import via `deck-port-powerpoint` skill when `.pptx` is attached
- Auto-expose preview URL after run stage completes

**Non-Goals:**
- Changing the Slides entity data model (fields are already sufficient)
- Modifying the sandbox proxy infrastructure (already works)
- PDF export (removed in previous changes)
- Changing the ACI sandbox provisioning flow

## Decisions

### 1. Pipeline stages: `["init", "slides", "run"]`
**Rationale:** The current `skills` stage adds no user-visible value — it's an internal prerequisite. Moving skills sync into init and adding a dedicated `run` stage that starts the dev server makes the pipeline match the actual workflow. The user sees: scaffolding → content creation → live preview.

**Alternative considered:** Keep 4 stages (init, skills, slides, run). Rejected because skills sync takes <5 seconds and is not interesting to the user.

### 2. Init stage: `create-deckio` + skills sync
**Approach:** Run `npx create-deckio@latest <deck_name> --title '...' --subtitle '...' --theme ... --appearance ... --palette ... --yes`, verify the directory, init git, then sync skills. All in one stage.

The deck config (title, subtitle, theme, appearance, palette) comes from the Slides entity fields, falling back to defaults from `SlidesAgent.parse_deck_config()` if a refined draft exists.

### 3. Slides stage: `copilot --autopilot --yolo` in deck directory
**Approach:** `cd` into the deck directory and run `copilot --autopilot --yolo` with the slides prompt. This is a long-running interactive session where Copilot generates all slide files.

If a `.pptx` attachment exists, append instructions to use the `deck-port-powerpoint` skill to import the PowerPoint content as input for the slide generation.

**Alternative considered:** Keep using `_sandbox_exec()` with `copilot -p <prompt>`. Rejected because the prompt-based approach doesn't leverage the full Copilot session context (skills, .github instructions, multi-turn).

### 4. Run stage: `npm install && npm run dev`
**Approach:** Run `npm install` followed by `npm run dev` in the deck directory. The dev server starts on port 3333. The stage waits for the server to become responsive (poll `/proxy/3333/`), then reports the preview URL.

The dev server runs as a long-lived process in the sandbox. The existing `/proxy/:port/*` endpoint in `sandbox/server.js` handles proxying.

**Alternative considered:** Keep the current "Run Live" button approach. Rejected because it separates dev server startup from the pipeline, causing timing issues and the port 3333 error.

### 5. Live preview: auto-expose after run stage
**Approach:** After the run stage confirms the dev server is running, the backend stores the preview URL on the task. The frontend auto-shows the preview iframe when the run stage completes — no "Run Live" button needed.

The `start_live` route in `dev.py` becomes a no-op or simple URL lookup since the server is already running from the pipeline.

## Risks / Trade-offs

- **[Long-running sandbox]** The run stage keeps the sandbox alive with a dev server. ACI containers have `SINGLE_TASK_MODE=true` which triggers shutdown 30s after the last task. → Mitigation: The run stage's dev server IS the last task — it stays running. The shutdown timer fix (already deployed) cancels shutdown when the dev server task is active.

- **[Copilot session timeout]** The `copilot --autopilot --yolo` session could stall or timeout on complex decks. → Mitigation: Keep the existing `stall_timeout` (600s) and total `timeout` (2400s) from `_sandbox_exec()`.

- **[Port conflict]** If a previous run left port 3333 occupied. → Mitigation: The init stage cleans the workspace. Each ACI sandbox is a fresh container.
