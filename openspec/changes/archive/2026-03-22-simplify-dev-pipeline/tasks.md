## 1. Backend Model & Service Changes

- [x] 1.1 Update `STAGE_NAMES` in `dev_service.py` — replace 8-stage list with `["init", "skills", "implement", "screenshots"]` for mockup mode
- [x] 1.2 Add `SEQUENTIAL_BASE_STAGES` constant: `["init", "skills"]` + dynamic `implement-foundation`, `implement-feature-N`, `screenshots` — add helper function `build_sequential_stages(features: list[str]) -> list[str]`
- [x] 1.3 Rename mode value `openspec` → `sequential` in `DevTask` model (`dev_task.py`), accept both values for backward compatibility
- [x] 1.4 Remove `openspec_status` field (`OpenSpecStatus` model) from `DevTask` — remove the model class and field
- [x] 1.5 Remove `set_openspec_status()` and `get_openspec_status()` methods from `DevService` and `InMemoryDevService`
- [x] 1.6 Update `_default_iteration()` in `dev_service.py` to use new stage names based on mode

## 2. Backend Dev Agent — Mockup Pipeline

- [x] 2.1 Rewrite `_run_mockup_pipeline()` to use 4 stages: init (squad init only, no openspec init), skills (unchanged), implement (single copilot invocation), screenshots (unchanged)
- [x] 2.2 Replace the propose+apply+archive stages with a single implement stage that runs: `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<mockup description>"`
- [x] 2.3 Remove the openspec init call (`openspec init --tools github-copilot --force`) from the init stage
- [x] 2.4 Remove the `openspec-propose` skill invocation and `openspec-apply` / `openspec-archive` skill invocations

## 3. Backend Dev Agent — Sequential Pipeline

- [x] 3.1 Rename `_run_openspec_pipeline()` → `_run_sequential_pipeline()` and update the `run_pipeline()` routing to call it for mode `sequential` (and legacy `openspec`)
- [x] 3.2 Rewrite foundation phase: init (squad only) → skills → implement-foundation using `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<foundation description>"`
- [x] 3.3 Rewrite feature phase: sequential execution (not parallel) — each feature runs `copilot --autopilot --yolo --experimental --model <model> --agent squad --continue -p "<feature description>"` in the same workspace
- [x] 3.4 Remove parallel feature workspace logic — delete `_merge_feature_workspaces()`, remove asyncio.gather/Semaphore patterns, remove rsync merge step
- [x] 3.5 Remove all `openspec-propose` / `openspec-apply` / `openspec-archive` skill invocations from sequential pipeline

## 4. Backend Dev Agent — Cleanup

- [x] 4.1 Remove `_poll_openspec_status()` method entirely
- [x] 4.2 Remove all `openspec list --json` sandbox commands
- [x] 4.3 Remove openspec-related imports and references
- [x] 4.4 Update `run_incremental_feature_pipeline()` to use the new copilot `--continue` command instead of `openspec-propose` + `openspec-apply`
- [x] 4.5 Update `_sandbox_exec()` payload construction to support the `--autopilot` flag and `--continue` parameter

## 5. Frontend Pipeline Visualization

- [x] 5.1 Update `STAGE_META` in `development/[id]/page.tsx` — remove `openspec`, `propose`, `apply`, `archive` entries; add `implement` entry with appropriate icon/color
- [x] 5.2 Update `FOUNDATION_STAGES` constant from `["init", "openspec", "skills", "squad", "propose", "apply", "archive"]` to `["init", "skills", "implement"]` (for mockup) or `["init", "skills", "implement-foundation"]` (for sequential)
- [x] 5.3 Update `FEATURE_STAGES` from `["propose", "apply"]` to single `["implement"]` per feature — render as `implement-feature-N` rows
- [x] 5.4 Update compact stage visualization in `development/page.tsx` (list view) to reflect 4-stage mockup / dynamic sequential stages
- [x] 5.5 Rename all UI labels from "OpenSpec" to "Sequential" — mode selector, task cards, detail headers

## 6. Frontend API & Types

- [x] 6.1 Update TypeScript types in `lib/api.ts` — rename mode `openspec` → `sequential`, remove `openspec_status` field from DevTask type
- [x] 6.2 Remove any OpenSpec status display components (changeName, totalTasks, completedTasks, currentTask, filesChanged)
- [x] 6.3 Update dev-task creation dialog/form to show "Sequential" instead of "OpenSpec" as mode option

## 7. Testing

- [x] 7.1 Update backend tests for mockup pipeline — verify 4-stage execution, verify copilot `--autopilot` command is used
- [x] 7.2 Update backend tests for sequential pipeline — verify dynamic stages, `--continue` flag on features, no parallel workspace merge
- [x] 7.3 Add backward compatibility test — verify tasks with mode `openspec` are treated as `sequential`
- [x] 7.4 Remove/update tests that reference openspec CLI commands, openspec_status, or 8-stage pipeline
