## MODIFIED Requirements

### Requirement: Sandbox Container App provisioning
The sandbox Container App (`ca-sandbox-{env}`) SHALL be retained as a fallback when `USE_ACI_SANDBOX` is disabled. When ACI mode is enabled, the Container App MAY be scaled to zero replicas to save cost, but SHALL remain deployed for rollback.

#### Scenario: Fallback mode uses Container App
- **WHEN** `USE_ACI_SANDBOX` is not set or is `false`
- **THEN** the backend routes all sandbox calls to the Container App via `SANDBOX_URL`

#### Scenario: ACI mode bypasses Container App
- **WHEN** `USE_ACI_SANDBOX=true`
- **THEN** the backend provisions per-task ACI containers and does not use the Container App sandbox

### Requirement: Sandbox lifecycle management
The sandbox lifecycle SHALL be managed per-task when ACI mode is enabled. Each ACI container group starts fresh, runs the full pipeline, and is deleted on completion. There is no persistent sandbox process to restart on skill changes.

#### Scenario: ACI container exits after pipeline
- **WHEN** a dev-task pipeline completes in ACI mode
- **THEN** the ACI container group is deleted and no sandbox process remains running for that task

### Requirement: Sandbox task count reflects dev-tasks
When ACI mode is enabled, the sandbox status endpoint is not available globally. Task count SHALL be tracked by the backend's in-memory `_active_sandbox_tasks` map instead of querying a shared sandbox.

#### Scenario: Task count from backend state
- **WHEN** the frontend queries active sandbox task count in ACI mode
- **THEN** the backend returns the count from `_active_sandbox_tasks` without calling a sandbox endpoint
