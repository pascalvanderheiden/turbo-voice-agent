## Context

The dev-task pipeline currently uses 8 stages (`init→openspec→skills→squad→propose→apply→archive→screenshots`) and relies heavily on the `openspec` CLI inside the sandbox for project scaffolding, proposal generation, task-by-task application, and archiving. This adds complexity: openspec must be installed in the sandbox Docker image, initialized per task, and its status polled throughout execution.

The Copilot CLI now supports `--autopilot --yolo --experimental --agent squad` flags, which can drive full implementation directly from a text prompt — eliminating the need for the intermediate openspec propose/apply/archive cycle inside the sandbox.

Current state:
- **Mockup mode**: 8 stages, uses `openspec-propose` + `openspec-apply` skills in Copilot CLI
- **OpenSpec mode**: 8 stages × foundation + parallel feature workspaces merged via rsync
- Both modes install and initialize `openspec` CLI in the sandbox

## Goals / Non-Goals

**Goals:**
- Reduce mockup pipeline from 8 stages to 4 (`init→skills→implement→screenshots`)
- Reduce sequential (formerly openspec) pipeline to dynamic stages (`init→skills→implement-foundation→implement-feature-N→screenshots`)
- Replace `openspec-propose` + `openspec-apply` + `openspec-archive` with single `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<prompt>"` invocations
- Remove openspec CLI from sandbox entirely (no install, no init, no status polling)
- Sequential features run in-place with `--continue` flag instead of parallel workspaces + rsync merge

**Non-Goals:**
- Changing the slides pipeline (stays as-is)
- Changing the squad initialization logic (stays as-is)
- Changing the skills installation logic (stays as-is)
- Changing the screenshot capture logic (stays as-is)
- Modifying the sandbox Container App provisioning or API

## Decisions

### D1: Single Copilot CLI command replaces openspec propose/apply/archive

**Decision**: Use `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<prompt>"` as the single implementation command for both modes.

**Rationale**: The `--autopilot` flag tells Copilot CLI to plan and execute autonomously. Combined with `--yolo` (no confirmations) and `--agent squad` (team routing), this achieves the same result as the 3-step openspec cycle but in one invocation. Less overhead, fewer failure points, faster execution.

**Alternative considered**: Keep openspec for sequential mode only — rejected because the same Copilot CLI command works for both modes, and removing openspec entirely simplifies the sandbox image and reduces maintenance.

### D2: Sequential features use `--continue` instead of parallel workspaces

**Decision**: Features in sequential mode execute one after another in the same workspace, each using `--continue` to preserve Copilot CLI context from the previous invocation.

**Rationale**: The current parallel workspace approach (copy workspace per feature → rsync merge) is fragile — merge conflicts, duplicate code, and broken imports are common. Sequential execution with `--continue` gives each feature full context of what was built before it, resulting in more coherent codebases.

**Trade-off**: Sequential is slower than parallel (features run one at a time instead of 2 concurrent). But quality improvement outweighs speed loss for most use cases.

### D3: Rename "openspec" mode to "sequential"

**Decision**: Rename the mode since it no longer uses the openspec CLI. "Sequential" accurately describes the execution pattern: foundation → feature 1 → feature 2 → etc.

**Migration**: Backend accepts both `openspec` and `sequential` as mode values during transition. Frontend shows only "Sequential". Existing tasks with `mode="openspec"` continue to work.

### D4: Dynamic stage names for sequential mode

**Decision**: Instead of fixed 8 stages, sequential mode uses dynamic stage names: `init`, `skills`, `implement-foundation`, `implement-feature-1`, `implement-feature-2`, …, `screenshots`. Each feature gets its own named stage.

**Rationale**: This maps 1:1 to actual execution steps, making progress tracking accurate. The frontend renders each implement stage as a distinct row.

### D5: Remove openspec_status from DevTask model

**Decision**: Drop the `openspec_status` field and `_poll_openspec_status()` method entirely.

**Rationale**: With openspec removed from the pipeline, there's nothing to poll. Stage-level status tracking (pending/running/completed/failed) is sufficient.

## Risks / Trade-offs

- **[Risk] Existing "openspec" mode tasks in Cosmos DB** → Mitigation: Backend accepts both `openspec` and `sequential` as valid mode values. No data migration needed.
- **[Risk] Sequential features slower than parallel** → Mitigation: Quality improvement justifies speed trade-off. Can revisit parallelism later with `--continue` context sharing.
- **[Risk] `--autopilot` flag behavior may change** → Mitigation: Pin to known-working Copilot CLI version in sandbox Docker image.
- **[Risk] `--continue` context window limits** → Mitigation: Each feature is a separate invocation; context accumulates but resets at reasonable boundaries. Monitor for issues with 5+ features.
