## Why

The slides dev-task pipeline has several issues that make it unreliable and hard to debug: the live preview never works (`{"error":"Dev server not reachable on port 3333"}`), the pipeline stages don't match the actual workflow (current: init → skills → slides; needed: init → slides → run), and the run stage that starts the dev server and exposes the preview endpoint is completely missing. The current code tries to start `npx slidev` directly in the backend live-preview route rather than as a pipeline stage, which means the dev server is never running when the user expects it.

## What Changes

- **Restructure pipeline stages** from `["init", "skills", "slides"]` to `["init", "slides", "run"]`. Skills sync moves into init (it's a prerequisite, not a user-visible stage).
- **Simplify init stage**: Run `npx create-deckio` with parameters from the Slides entity (title, subtitle, theme, appearance, palette), then sync skills. Remove the separate skills stage.
- **Redesign slides stage**: `cd` into the deck folder and run `copilot --autopilot --yolo` with a prompt to create slides from the Slides entity content. If a `.pptx` attachment exists, use the `deck-port-powerpoint` skill (available after init) to convert it as additional input.
- **Add run stage**: Run `npm install && npm run dev` inside the deck folder to start the Slidev dev server on port 3333, then expose the live preview endpoint. This replaces the broken "start live" button approach — the dev server is part of the pipeline, not an afterthought.
- **Fix live preview proxy**: The sandbox already has `/proxy/:port/*` support. The run stage ensures the server is actually running before the preview URL is returned.

## Capabilities

### New Capabilities
- `slides-run-stage`: Pipeline stage that installs dependencies, starts the Slidev dev server, and exposes the live preview endpoint as part of the normal pipeline flow.

### Modified Capabilities
- `slides-pipeline`: Restructure from init→skills→slides to init→slides→run. Move skills sync into init. Add run stage for dev server.
- `slides-live-preview`: Preview is now served by the run pipeline stage instead of a separate "start live" action. The dev server runs as a long-lived process in the sandbox.

## Impact

- `backend/app/agents/dev_agent.py` — Major rewrite of `_run_slides_pipeline()`: new stage order, init includes skills sync, slides uses `copilot --autopilot --yolo`, new run stage
- `backend/app/services/dev_service.py` — Update `SLIDES_STAGE_NAMES` from `["init", "skills", "slides"]` to `["init", "slides", "run"]`
- `backend/app/routes/dev.py` — Simplify live preview route: run stage already starts the server, so "start live" just returns the proxy URL
- `frontend/src/app/(app)/development/[id]/page.tsx` — Auto-show preview iframe after run stage completes instead of requiring a "Run Live" button click
- `sandbox/server.js` — No changes needed (proxy already works)
