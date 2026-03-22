## Why

The dev-task pipeline is overly complex. It installs and relies on the `openspec` CLI inside the sandbox for proposal generation, task tracking, and archiving — adding overhead, latency, and fragile multi-step orchestration. The Copilot CLI now supports `--autopilot --yolo --experimental --agent squad` which can drive implementation directly from a description prompt, eliminating the need for openspec inside the sandbox entirely.

## What Changes

- **BREAKING**: Rename the `openspec` pipeline mode to `sequential` across backend model, agent, service, and frontend
- **BREAKING**: Remove all openspec CLI installation, initialization, status polling, propose/apply/archive skill invocations from the sandbox pipeline
- Simplify **mockup** pipeline from 8 stages (`init→openspec→skills→squad→propose→apply→archive→screenshots`) to 4 stages (`init→skills→implement→screenshots`):
  - `init`: Only squad install + `squad init` (no openspec init)
  - `skills`: Unchanged — install marketplace + local skills
  - `implement`: Single Copilot CLI invocation: `copilot --autopilot --yolo --experimental --model claude-opus-4.6 --agent squad -p "<mockup prompt>"`
  - `screenshots`: Unchanged — start app, capture with Playwright
- Simplify **sequential** pipeline to: `init→skills→implement-foundation→implement-feature-1→…→implement-feature-N→screenshots`:
  - Foundation uses the same Copilot CLI command as mockup, with the foundation description
  - Each feature uses the same command plus `--continue` to preserve context
  - No parallel feature workspaces, no rsync merge — features build sequentially on the same workspace
- Remove `openspec_status` field and polling from `DevTask` model
- Remove `_poll_openspec_status()` from dev agent
- Remove the `openspec` and `archive` stage definitions from `STAGE_NAMES`
- Update frontend pipeline visualization to reflect new stage names and sequential feature flow

## Capabilities

### New Capabilities

_None — this change simplifies existing capabilities._

### Modified Capabilities

- `dev-service`: Remove `openspec_status` from DevTask model, rename mode `openspec` → `sequential`, replace 8-stage `STAGE_NAMES` with new 4-stage list, remove `archive` stage
- `squad-pipeline-stages`: Replace 8-stage pipeline definition with simplified stages (mockup: init→skills→implement→screenshots, sequential: init→skills→implement-foundation→implement-feature-N→screenshots)
- `pipeline-phase-display`: Update phase-based visualization for new stage names — remove openspec/propose/apply/archive nodes, add implement node, sequential features show as implement-feature-N stages
- `copilot-cli-sandbox`: Remove openspec CLI installation from sandbox, update Copilot CLI invocation to use `--autopilot --yolo --experimental --agent squad` flags directly

## Impact

- **Backend**: `dev_agent.py` (major rewrite of `_run_mockup_pipeline` and `_run_openspec_pipeline` → `_run_sequential_pipeline`), `dev_service.py` (stage names), `dev_task.py` (model changes)
- **Frontend**: `development/[id]/page.tsx` (stage visualization), `development/page.tsx` (compact stage display) — update `STAGE_META`, `FOUNDATION_STAGES`, `FEATURE_STAGES`
- **Removed dependencies**: openspec CLI no longer needed in sandbox Docker image
- **No API changes**: REST endpoints stay the same, only internal pipeline behavior changes
