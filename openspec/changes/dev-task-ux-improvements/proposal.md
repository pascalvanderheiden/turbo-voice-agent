## Why

The dev-task pipeline UI has several usability gaps: squad members show no live activity, the foundation/features pipeline stages are confusingly interleaved, stage labels overflow on smaller screens, and reopening a running dev-task loses the terminal stream. These issues reduce confidence during demos and daily use — you can't tell who's working on what, which phase is active, or reconnect to a running task.

## What Changes

- **Squad live status**: Run `copilot --agent squad --yolo` in sandbox and periodically poll `squad status` to detect which agents are active. Update squad member dots (idle → working → done) in real-time on both detail and overview pages.
- **Pipeline phase display overhaul**: Foundation stages shown as one pipeline row; once done, mark it complete. Each feature iteration then shows its own propose→apply pipeline. Screenshots stage only appears after all features complete. Clear visual separation between phases.
- **Responsive stage labels**: Shorten stage names, allow wrapping/continuation on narrow screens instead of horizontal overflow.
- **Stream reconnection**: When navigating back to a running dev-task, replay the existing output buffer so users see all prior output, not just "Waiting for sandbox output."
- **Squad on overview cards**: Show active squad members (those currently working) on dev-task list cards for at-a-glance status.

## Capabilities

### New Capabilities
- `squad-live-status`: Live squad member activity tracking via `squad status` CLI polling and `--agent squad` mode during pipeline execution
- `pipeline-phase-display`: Redesigned pipeline visualization with distinct foundation/features/screenshots phases
- `stream-reconnection`: Reliable terminal output replay when reopening a running dev-task

### Modified Capabilities

## Impact

- **Frontend**: `development/[id]/page.tsx` (detail), `development/page.tsx` (overview), SquadPanel, TerminalView, pipeline SVG
- **Backend**: `dev_agent.py` (squad status polling, `--agent squad` flag), `dev.py` (stream endpoint reconnection)
- **Models**: `dev_task.py` (SquadMember status field already exists, may need timestamp)
- **API**: DevTask response includes updated squad member statuses during pipeline execution
