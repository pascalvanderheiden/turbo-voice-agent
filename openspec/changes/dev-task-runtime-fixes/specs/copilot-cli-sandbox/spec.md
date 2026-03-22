## MODIFIED Requirements

### Requirement: Sandbox task count reflects dev-tasks
The sandbox status SHALL report the number of currently running dev-task pipelines, not the internal sandbox task count. One running dev-task equals one active task.

#### Scenario: One dev-task running
- **WHEN** one dev-task pipeline is running (which may use multiple internal sandbox calls)
- **THEN** the sandbox status SHALL report activeTasks as 1

### Requirement: Sandbox stop terminates all pipeline tasks
The sandbox stop endpoint SHALL terminate all running dev-task pipelines and their associated sandbox tasks, confirming each kill completes.

#### Scenario: Stop with multiple running tasks
- **WHEN** the stop endpoint is called with 2 running pipelines
- **THEN** all associated AsyncIO tasks and sandbox tasks SHALL be terminated, and the sandbox activeTasks SHALL drop to 0
