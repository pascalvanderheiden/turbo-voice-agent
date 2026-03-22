## Why

The dev-task runtime has several gaps: the slides agent is missing from the agent architecture page, the sandbox task count and stop logic are unreliable, premium request tracking uses a static model-based multiplier instead of actual CLI output, and squad member activity visible in the Copilot CLI stream is not captured or displayed in the dev-task detail UI.

## What Changes

- Add slides agent to the agent architecture page (icon, color, tile)
- Fix sandbox task count to accurately reflect running dev-tasks (one dev-task = one sandbox task, not the internal sandbox count)
- Fix sandbox stop to reliably terminate all active sandbox tasks
- Replace model-based premium request calculation with stream-based parsing of Copilot CLI's "Total usage est: N Premium requests" output, summing across all stages
- Parse squad agent activity from the Copilot CLI stream in real-time (e.g., "Trinity: Build sexy todo app UI") and surface it as live squad member status in the dev-task detail
- Show premium request count on each dev-task card in the overview list and in the detail page header
- Show total elapsed time on each dev-task card in the overview list
- Refine settings premium request bar chart: only show months with data, use 2000 as minimum Y-axis max, remove opus 3× comment

## Capabilities

### New Capabilities

- `stream-premium-parsing`: Parse premium request counts from Copilot CLI stream output instead of static model multipliers
- `stream-squad-activity`: Parse squad agent names and tasks from Copilot CLI stream in real-time, update squad member status

### Modified Capabilities

- `squad-visualization`: Add slides agent tile to agent architecture page
- `pipeline-phase-display`: Show live squad activity in dev-task detail panel; show premium request count in overview cards and detail header; show total elapsed time in overview cards
- `copilot-cli-sandbox`: Fix task count reporting and stop/terminate reliability

## Impact

- Backend: `dev_agent.py` (stream parsing in `_sandbox_exec`, premium tracking, squad activity extraction), `sandbox.py` (task count, stop logic)
- Frontend: `agents/page.tsx` (slides tile), `development/[id]/page.tsx` (squad activity, premium count), `development/page.tsx` (premium count, elapsed time on cards)
- Models: `dev_task.py` (SquadMember may need activity/task field)
