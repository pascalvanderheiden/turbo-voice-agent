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
## MODIFIED Requirements

### Requirement: Sandbox runtime backed by dynamic sessions
The sandbox runtime in deployed environments SHALL be Azure Container Apps dynamic sessions. The previous shared Container App sandbox (`ca-sandbox-*`) and the ACI per-task implementation SHALL NOT be provisioned. Local development SHALL continue to use the docker-compose `sandbox` service.

#### Scenario: Deployed env uses session pool
- **WHEN** the backend is deployed via `azd up`
- **THEN** sandbox HTTP calls SHALL go through `SESSION_POOL_MANAGEMENT_ENDPOINT`
- **AND** there SHALL NOT be a deployed `ca-sandbox-*` Container App
- **AND** there SHALL NOT be any ACI container groups created by the backend

#### Scenario: Sandbox exposes task API
- **WHEN** any sandbox session is running
- **THEN** it SHALL accept POST requests to `/tasks` with command payloads
- **AND** SHALL stream CLI output via SSE on `/tasks/{id}/stream`

#### Scenario: Local dev unchanged
- **WHEN** the backend runs under docker-compose
- **THEN** sandbox calls SHALL resolve to `http://sandbox:3000` via service discovery

### Requirement: Sandbox lifecycle managed by session pool
The sandbox lifecycle SHALL be per-task and managed by the session pool. Each dev-task allocates a session on first sandbox call, retains it for the duration of the task, and the pool destroys the session after cooldown inactivity. The backend SHALL NOT poll for session health on a schedule.

#### Scenario: Session destroyed after task completes
- **WHEN** a dev-task pipeline completes (success or failure) and no further requests are made
- **THEN** the session pool SHALL destroy the session after the configured cooldown period
- **AND** the backend SHALL NOT take any action to delete it

#### Scenario: Explicit stop on cancellation
- **WHEN** the user cancels or deletes a running dev-task
- **THEN** the backend SHALL call `POST /.management/stopSession?identifier={T}` to release resources immediately

### Requirement: Skills synchronization
The system SHALL make the user's installed skills available inside each sandbox session at `/home/agent/.copilot/skills/`. Skills are synchronized at session warm-up by the same entrypoint script the image already uses, and hot-reloaded at runtime via the sandbox `/skills/sync` endpoint. Dev-task pipelines SHALL NOT include a skills installation stage.

#### Scenario: Skills present on first session request
- **WHEN** the first request lands on a newly-warmed session
- **THEN** the user's skills SHALL be present at `/home/agent/.copilot/skills/` from the warm-up sync

#### Scenario: Skills refreshed via hot-reload
- **WHEN** a user installs a new skill while a session is active
- **THEN** the backend SHALL POST `/skills/sync` to that session
- **AND** the skill SHALL be available within seconds without a session restart

#### Scenario: No skills installation during dev-task pipeline
- **WHEN** a dev-task pipeline starts (mockup, sequential, or slides mode)
- **THEN** the pipeline SHALL NOT include a "skills" stage
- **AND** SHALL NOT call `_install_skills_in_sandbox()` or `_verify_skills_in_sandbox()`
- **AND** skills SHALL already be present from warm-up sync or hot-reload

### Requirement: Real-time CLI output streaming
The system SHALL stream GitHub Copilot CLI output from the active session to the frontend in real-time so users can observe the CLI processing their requests.

#### Scenario: Live output during Mockup mode
- **WHEN** a Mockup dev task is executing in a session
- **THEN** the CLI's stdout/stderr SHALL be streamed via SSE through the session pool to the frontend and displayed in a terminal-style viewer

#### Scenario: Live output during OpenSpec mode
- **WHEN** an OpenSpec dev task is executing with parallel feature builds
- **THEN** output from each parallel feature build SHALL be distinguishable in the stream, labeled by feature name

### Requirement: Code artifact download
The system SHALL allow users to download the generated code from completed dev tasks as a zip archive. The session that produced the artifact MAY have been destroyed before download; artifacts are persisted to Blob Storage on task completion.

#### Scenario: Download after Mockup completion
- **WHEN** a Mockup dev task completes successfully
- **THEN** the user SHALL be able to download the generated project as a `.zip` file via the dev task detail view
- **AND** the download SHALL succeed even after the session that produced it has been destroyed

#### Scenario: Download after OpenSpec completion
- **WHEN** an OpenSpec dev task completes successfully
- **THEN** the user SHALL be able to download the full project (foundation + all features) as a `.zip` file

### Requirement: Screenshot capture with Playwright
The system SHALL capture screenshots of the generated application using Playwright after each dev task completes, and display them in the frontend.

#### Scenario: Screenshots after build completion
- **WHEN** a dev task finishes building
- **THEN** the session SHALL start the generated app's dev server, capture full-page screenshots of key routes using Playwright, and return them as part of the task result before the session is allowed to cool down

#### Scenario: Screenshot gallery in UI
- **WHEN** a user views a completed dev task
- **THEN** they SHALL see a gallery of screenshots captured from the generated application

### Requirement: Sandbox task count reflects dev-tasks
The sandbox status endpoint SHALL report the count of active dev-tasks tracked by the backend's in-memory `_active_sandbox_tasks` map. The backend SHALL NOT query individual sessions for status — task count is a property of the backend's pipeline state, not the session pool.

#### Scenario: Task count from backend state
- **WHEN** the frontend queries active sandbox task count
- **THEN** the backend SHALL return the count from `_active_sandbox_tasks` without calling any session endpoint

#### Scenario: One dev-task running
- **WHEN** one dev-task pipeline is running with an allocated session
- **THEN** the sandbox status SHALL report activeTasks as 1

### Requirement: Sandbox stop terminates all pipeline tasks
The sandbox stop endpoint SHALL terminate all running dev-task pipelines and explicitly call `stopSession` for each associated session identifier, confirming each kill completes.

#### Scenario: Stop with multiple running tasks
- **WHEN** the stop endpoint is called with 2 running pipelines
- **THEN** all associated AsyncIO tasks SHALL be cancelled
- **AND** `POST /.management/stopSession` SHALL be called for each task identifier
- **AND** the sandbox activeTasks SHALL drop to 0

## REMOVED Requirements

### Requirement: Sandbox Container App provisioning
**Reason**: Replaced by the `Microsoft.App/sessionPools` resource defined in `session-pool-infra`. The shared Container App is no longer needed because sessions provide better isolation and faster cold-start.
**Migration**: Delete `container-app-sandbox.bicep` and all references in `main.bicep`. Existing deployed `ca-sandbox-*` Container Apps can be deleted manually after deployment verification.
