## Context

The dev-task pipeline runs Copilot CLI inside a sandbox container, streaming output via SSE. The CLI outputs rich information — squad agent activity ("Trinity: Build sexy todo app UI"), premium request usage ("Total usage est: 3 Premium requests") — but none of this is parsed. Premium tracking uses a static multiplier (opus=3, others=1) which is inaccurate since squads use sub-agents with various models. Squad member status relies on `squad status --json` which doesn't return real-time activity. The agent architecture page is missing the slides agent tile. The sandbox task count reflects internal sandbox state, not actual dev-tasks.

## Goals / Non-Goals

**Goals:**
- Parse premium request count from CLI stream output per `_sandbox_exec` invocation
- Parse squad agent activity (name + task) from CLI stream in real-time
- Surface live squad activity in dev-task detail UI
- Add slides agent to agent architecture page
- Fix sandbox task count and stop reliability

**Non-Goals:**
- Changing the sandbox container itself (only backend/frontend)
- Parsing full token breakdowns per model (just the total premium count)
- Changing squad team member generation logic

## Decisions

### 1. Parse "Total usage est" from CLI stream output

The Copilot CLI outputs a summary block at the end:
```
Total usage est:    3 Premium requests
API time spent:     5m 10s
```

In `_sandbox_exec`, after the SSE stream completes, scan `output_lines` for the regex `Total usage est:\s+(\d+)\s+Premium requests`. Use this to call `add_premium_requests()` with the actual count. Remove the static `_get_premium_multiplier()` approach.

**Why**: The CLI already knows the exact premium cost including all sub-agent usage. Parsing it is more accurate than any heuristic.

### 2. Parse squad agent activity from stream

Squad agent lines follow a pattern like:
```
● General-purpose(claude-sonnet-4.5) 🎨Trinity: Build sexy todo app UI
```

Parse lines matching agents with names (Trinity, Morpheus, Scribe, etc.) and their task descriptions. Store as `activity` field on `SquadMember`. Update via `set_squad()` as activity is detected.

**Why**: `squad status --json` doesn't return current activity. The stream is the only source of truth for what each agent is doing.

### 3. Track sandbox tasks at backend level, not sandbox level

The sandbox reports all internal tasks (including sub-tasks, retries). Instead, count dev-tasks with `status == "running"` from the dev service. The stop endpoint already cancels AsyncIO tasks + sandbox tasks — ensure it waits for confirmation.

**Why**: One dev-task = one pipeline, regardless of how many sandbox sub-tasks it creates internally.

### 4. Add slides agent to architecture page

Add `slides: IconPresentation` to AGENT_ICONS and appropriate color. The slides agent already exists in the backend — just missing from the UI grid.

## Risks / Trade-offs

- [Stream format changes] → Regex patterns may break if CLI output format changes. Use lenient matching with fallback.
- [Race conditions in activity parsing] → Multiple squad agents emit activity concurrently. Parse and update atomically per line.
- [Premium parsing at end of stream] → If a task is killed/times out, the summary may not appear. Fall back to 1 premium request per invocation in that case.
