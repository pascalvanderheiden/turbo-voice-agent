## ADDED Requirements

### Requirement: Terminal output replay on reconnection
When a user navigates back to a running dev-task, the TerminalView component reconnects to the SSE stream and receives all historical output from the backend buffer, followed by live output.

#### Scenario: User reopens running dev-task
- **WHEN** A user navigates to a dev-task detail page where the task status is "running"
- **THEN** The TerminalView connects to the stream endpoint, receives all buffered output lines from the beginning, and displays them immediately before continuing with live output

#### Scenario: User opens dev-task that was started before page load
- **WHEN** A dev-task was triggered and has been producing output, and the user navigates to its detail page for the first time
- **THEN** All prior output from the pipeline buffer is streamed to the terminal, not just "Waiting for sandbox output"

#### Scenario: Stream connection drops and recovers
- **WHEN** The EventSource connection drops (network issue, Azure proxy timeout)
- **THEN** The TerminalView reconnects within 5 seconds and receives output from where the buffer cursor left off (no duplicate lines since cursor tracks position)

### Requirement: Backend buffer cap
The pipeline output buffer in `_pipeline_outputs` is capped at 2000 entries per task to prevent unbounded memory growth for long-running tasks.

#### Scenario: Buffer exceeds cap
- **WHEN** A pipeline appends the 2001st entry to the output buffer
- **THEN** The oldest entries are trimmed to maintain the 2000-entry cap
