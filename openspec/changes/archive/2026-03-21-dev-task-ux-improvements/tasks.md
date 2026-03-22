## 1. Stream Reconnection Fix

- [x] 1.1 Cap backend pipeline output buffer at 2000 entries in `dev_agent.py` — trim oldest when exceeded
- [x] 1.2 Fix TerminalView to always attempt SSE connection when task status is "running", regardless of prior state — remove dependency on `isRunning` toggle for initial connection
- [x] 1.3 On TerminalView mount, show "Reconnecting..." instead of "Waiting for sandbox output" when task is already running
- [x] 1.4 Test: navigate away from running task and back — verify all historical + live output appears

## 2. Pipeline Phase Display Redesign

- [x] 2.1 Replace single flat 8-stage SVG with phase-based layout: Foundation section (init→openspec→skills→squad→propose→apply→archive), Features section (compact propose→apply per iteration), Screenshots section (gated on all features complete)
- [x] 2.2 Shorten stage labels for narrow screens: Init, Spec, Skills, Squad, Prop, Apply, Arch — use `flex-wrap` so nodes continue to next row when they don't fit
- [x] 2.3 When foundation iteration (0) is fully complete, collapse it to a "✓ Foundation" badge instead of showing all 7 nodes
- [x] 2.4 Each feature iteration shows a compact row: feature name + propose→apply status. Completed features show "✓" badge
- [x] 2.5 Screenshots node only appears/activates when all features are complete
- [x] 2.6 Update dev-task overview cards (`development/page.tsx`) to use the same phase-based compact visualization

## 3. Squad Live Status

- [x] 3.1 After each apply sub-task in `_run_openspec_pipeline`, run `squad status --json` in sandbox, parse output, and update SquadMember statuses via `svc.set_squad()`
- [x] 3.2 When squad config exists in workspace (`.squad/config.json`), add `--agent squad` flag to Copilot CLI `_sandbox_exec` prompts during apply stages
- [x] 3.3 Update SquadPanel dots: green pulsing = working, solid green = done, gray = idle — animate working state with CSS pulse
- [x] 3.4 Add compact squad member row to dev-task overview cards showing only "working" members with role emoji + name

## 4. Backend Pipeline Stage Accuracy

- [x] 4.1 Ensure foundation stages are marked complete/failed accurately — when foundation propose+apply finish, mark archive as complete before moving to features
- [x] 4.2 Track feature pipeline stages independently: each feature iteration's propose→apply status updates in real-time
- [x] 4.3 Only transition to screenshots stage when all feature iterations report "completed"
