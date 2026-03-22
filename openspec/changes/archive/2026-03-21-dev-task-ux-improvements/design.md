## Context

The dev-task detail and overview pages currently show squad members with static status (always "idle"), display all 8 pipeline stages in one flat row regardless of phase, truncate/overflow stage labels on narrow screens, and lose terminal output when navigating away from a running task. The backend pipeline (`dev_agent.py`) uses `squad init/hire/doctor` but never polls `squad status` or uses `--agent squad` mode during execution. The stream endpoint (`/stream`) already preserves the output buffer in memory — the reconnection issue is purely frontend.

## Goals / Non-Goals

**Goals:**
- Show live squad member activity (who is working, idle, done) by integrating `squad status` polling during pipeline execution
- Use `copilot --agent squad --yolo` parameter when running Copilot CLI in squad-enabled dev-tasks
- Redesign pipeline visualization: Foundation phase → Feature phases → Screenshots, each clearly separated
- Make stage labels responsive: shorter names, wrap to next line on narrow screens
- Fix stream reconnection so reopening a running dev-task shows prior + live output
- Show active squad members on dev-task overview cards

**Non-Goals:**
- Rewriting the squad-pr CLI itself
- Adding real-time WebSocket for squad status (polling from backend is sufficient)
- Changing the squad hiring/team generation logic

## Decisions

1. **Squad status polling**: After each `_sandbox_exec` call within the apply stage, run `squad status --json` to get current member activity. Parse output and update squad metadata via `svc.set_squad()`. This piggybacks on existing sandbox exec infrastructure.

2. **`--agent squad` mode**: When running Copilot CLI prompts in squad-enabled tasks, append `--agent squad` to the command. This activates squad-pr's agent routing so work is delegated to the correct team member.

3. **Pipeline phase display**: Replace single flat stage row with 3 collapsible sections:
   - **Foundation**: init → openspec → skills → squad → propose → apply → archive (iteration 0)
   - **Features**: Each feature iteration gets its own compact row showing propose → apply
   - **Screenshots**: Single node, only shown/enabled when all features complete
   
4. **Stream reconnection fix**: The backend buffer already works — the issue is the frontend `isRunning` guard. The TerminalView should connect whenever the task status is `running` OR the buffer has historical data. On mount, always attempt connection; if buffer has data, it streams immediately.

5. **Overview card squad display**: Show a compact row of squad member avatars/initials with colored dots (green=working, gray=idle) underneath the pipeline stages on each card.

## Risks / Trade-offs

- **Squad status polling frequency**: Too frequent = extra sandbox exec overhead. Plan: poll after each apply sub-task (natural pause points), not continuously.
- **`--agent squad` compatibility**: If squad-pr isn't installed in sandbox, the flag may cause errors. Mitigate: check if squad config exists before adding the flag.
- **Buffer memory**: Large output buffers for long-running tasks could consume memory. Current 500-line cap on frontend is fine; backend buffer should cap at ~2000 entries.
