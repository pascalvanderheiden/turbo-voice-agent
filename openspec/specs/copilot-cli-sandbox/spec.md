## ADDED Requirements

### Requirement: Sandbox Container App provisioning
The sandbox Container App (`ca-sandbox-{env}`) SHALL be retained as a fallback when `USE_ACI_SANDBOX` is disabled. When ACI mode is enabled, the Container App MAY be scaled to zero replicas to save cost, but SHALL remain deployed for rollback.

#### Scenario: Fallback mode uses Container App
- **WHEN** `USE_ACI_SANDBOX` is not set or is `false`
- **THEN** the backend routes all sandbox calls to the Container App via `SANDBOX_URL`

#### Scenario: ACI mode bypasses Container App
- **WHEN** `USE_ACI_SANDBOX=true`
- **THEN** the backend provisions per-task ACI containers and does not use the Container App sandbox

#### Scenario: Sandbox exposes task API
- **WHEN** the sandbox Container App is running
- **THEN** it SHALL accept POST requests to `/tasks` with command payloads and stream CLI output via SSE on `/tasks/{id}/stream`

### Requirement: Sandbox lifecycle management
The sandbox lifecycle SHALL be managed per-task when ACI mode is enabled. Each ACI container group starts fresh, runs the full pipeline, and is deleted on completion. There is no persistent sandbox process to restart on skill changes.

#### Scenario: ACI container exits after pipeline
- **WHEN** a dev-task pipeline completes in ACI mode
- **THEN** the ACI container group is deleted and no sandbox process remains running for that task

#### Scenario: Sandbox health check (Container App fallback)
- **WHEN** the backend attempts to delegate a task to the Container App sandbox
- **THEN** it SHALL first verify sandbox health via a `/health` endpoint and recreate the sandbox if unhealthy

### Requirement: Skills synchronization
The system SHALL make the user's installed skills available inside the sandbox container at `/home/agent/.copilot/skills/`. Skills are synchronized at container startup via the entrypoint script and hot-reloaded at runtime via the sandbox `/skills/sync` endpoint. Dev-task pipelines SHALL NOT include a skills installation stage.

#### Scenario: Skills copied at sandbox creation
- **WHEN** a new sandbox container is started
- **THEN** all skills from the host `.agents/skills/` directory (local) or Blob Storage (Azure) SHALL be available at `/home/agent/.copilot/skills/`

#### Scenario: Skills refreshed on rebuild
- **WHEN** the sandbox container is rebuilt or restarted after new skills are installed
- **THEN** the updated skill set SHALL be available inside the container

#### Scenario: No skills installation during dev-task pipeline
- **WHEN** a dev-task pipeline starts (mockup, sequential, or slides mode)
- **THEN** the pipeline SHALL NOT include a "skills" stage
- **AND** the pipeline SHALL NOT call `_install_skills_in_sandbox()` or `_verify_skills_in_sandbox()`
- **AND** skills SHALL already be present from startup sync or hot-reload

### Requirement: Real-time CLI output streaming
The system SHALL stream GitHub Copilot CLI output from the sandbox to the frontend in real-time so users can observe the CLI processing their requests.

#### Scenario: Live output during Mockup mode
- **WHEN** a Mockup dev task is executing in the sandbox
- **THEN** the CLI's stdout/stderr SHALL be streamed via SSE to the frontend and displayed in a terminal-style viewer

#### Scenario: Live output during OpenSpec mode
- **WHEN** an OpenSpec dev task is executing with parallel feature builds
- **THEN** output from each parallel feature build SHALL be distinguishable in the stream, labeled by feature name

### Requirement: Code artifact download
The system SHALL allow users to download the generated code from completed dev tasks as a zip archive.

#### Scenario: Download after Mockup completion
- **WHEN** a Mockup dev task completes successfully
- **THEN** the user SHALL be able to download the generated project as a `.zip` file via the dev task detail view

#### Scenario: Download after OpenSpec completion
- **WHEN** an OpenSpec dev task completes successfully
- **THEN** the user SHALL be able to download the full project (foundation + all features) as a `.zip` file

### Requirement: Screenshot capture with Playwright
The system SHALL capture screenshots of the generated application using Playwright after each dev task completes, and display them in the frontend.

#### Scenario: Screenshots after build completion
- **WHEN** a dev task (Mockup or OpenSpec) finishes building
- **THEN** the sandbox SHALL start the generated app's dev server, capture full-page screenshots of key routes using Playwright, and return them as part of the task result

#### Scenario: Screenshot gallery in UI
- **WHEN** a user views a completed dev task
- **THEN** they SHALL see a gallery of screenshots captured from the generated application

---

## MODIFIED Requirements (from dev-task-runtime-fixes)

### Requirement: Sandbox task count reflects dev-tasks
When ACI mode is enabled, the sandbox status endpoint is not available globally. Task count SHALL be tracked by the backend's in-memory `_active_sandbox_tasks` map instead of querying a shared sandbox.

#### Scenario: Task count from backend state
- **WHEN** the frontend queries active sandbox task count in ACI mode
- **THEN** the backend returns the count from `_active_sandbox_tasks` without calling a sandbox endpoint

#### Scenario: One dev-task running (Container App fallback)
- **WHEN** one dev-task pipeline is running using the Container App sandbox
- **THEN** the sandbox status SHALL report activeTasks as 1

### Requirement: Sandbox stop terminates all pipeline tasks
The sandbox stop endpoint SHALL terminate all running dev-task pipelines and their associated sandbox tasks, confirming each kill completes.

#### Scenario: Stop with multiple running tasks
- **WHEN** the stop endpoint is called with 2 running pipelines
- **THEN** all associated AsyncIO tasks and sandbox tasks SHALL be terminated, and the sandbox activeTasks SHALL drop to 0
