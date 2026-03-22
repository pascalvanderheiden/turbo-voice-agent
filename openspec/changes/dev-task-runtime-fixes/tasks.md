## 1. Model & Backend Foundation

- [x] 1.1 Add `activity` field (str, default "") to `SquadMember` in `backend/app/models/dev_task.py`
- [x] 1.2 Add `activity` to `SquadMember` in `frontend/src/lib/api.ts` TypeScript type

## 2. Stream Premium Parsing

- [x] 2.1 Remove `_PREMIUM_MULTIPLIERS` dict and `_get_premium_multiplier()` function from `dev_agent.py`
- [x] 2.2 Remove the static premium calculation block in `_sandbox_exec()` (the `premium_cost = _get_premium_multiplier(model)` block)
- [x] 2.3 After SSE stream completes in `_sandbox_exec()`, scan `output_lines` for regex `Total usage est:\s+(\d+)\s+Premium requests` and extract the count
- [x] 2.4 Call `add_premium_requests(task_id, parsed_count)` with parsed value, fallback to 1 if not found and prompt was used
- [x] 2.5 Add unit test for premium parsing regex with sample CLI output

## 3. Stream Squad Activity Parsing

- [x] 3.1 In `_sandbox_exec()`, add real-time parsing of squad agent activity lines during SSE streaming (not after). Match patterns like `AgentName: Task description` with emoji prefixes
- [x] 3.2 When activity is detected, update the corresponding `SquadMember` activity and status via `set_squad()` on the service
- [x] 3.3 Pass `task_id` and `user_id` context to enable squad updates inside `_sandbox_exec()` (add params or use instance state)

## 4. Sandbox Task Count & Stop

- [x] 4.1 In `backend/app/routes/sandbox.py` `get_sandbox_status()`, count running dev-task pipelines (from `_pipeline_tasks` dict) instead of relying solely on sandbox `/health` activeTasks
- [x] 4.2 In `stop_sandbox()`, after cancelling AsyncIO tasks, verify each sandbox task DELETE returns success; retry once if needed
- [x] 4.3 After stop completes, clear `_active_sandbox_tasks` dict and `_pipeline_tasks` dict

## 5. Agent Architecture Page

- [x] 5.1 Add `slides: IconPresentation` to `AGENT_ICONS` in `frontend/src/app/(app)/agents/page.tsx`
- [x] 5.2 Add `slides` color entry to `AGENT_COLORS` (use cyan)
- [x] 5.3 Add `marketing: IconVideo` to `AGENT_ICONS` if missing (check existing)

## 6. Squad Activity & Premium/Time Display

- [x] 6.1 In `StatusPanel` in `frontend/src/app/(app)/development/[id]/page.tsx`, display `member.activity` text below role when member is working
- [x] 6.2 In `WorkingSquadDisplay` in `frontend/src/app/(app)/development/page.tsx`, show activity text in the inline working members display
- [x] 6.3 Add premium request count badge to each dev-task card in the overview list (`development/page.tsx`)
- [x] 6.4 Add premium request count to the dev-task detail header (`development/[id]/page.tsx`)
- [x] 6.5 Add total elapsed time display to each dev-task card in the overview list (calculate from earliest startedAt to latest completedAt or now)

## 7. Settings Premium Chart Refinement

- [x] 7.1 In `PremiumUsageChart` in `settings/page.tsx`, filter months to only include those with `count > 0`; if none have data show just the current month
- [x] 7.2 Change `maxCount` to use `Math.max(...counts, 2000)` so bars have reasonable height even with low data
- [x] 7.3 Remove the "Opus models count as 3× per request" text from the chart description

## 8. Validation

- [x] 7.1 Run backend tests (`pytest tests/test_dev_agent_incremental.py tests/test_slides_service.py`) and verify all pass
- [x] 7.2 Run frontend TypeScript check (`npx tsc --noEmit`) and verify zero errors
