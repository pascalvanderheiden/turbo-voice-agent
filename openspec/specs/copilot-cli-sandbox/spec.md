## ADDED Requirements

### Requirement: Sandbox Container App provisioning
The system SHALL provision a dedicated Azure Container App for running the GitHub Copilot CLI in a Docker sandbox with yolo mode enabled. The sandbox Container App SHALL be isolated from the backend Container App and expose an HTTP API for receiving task commands.

#### Scenario: Sandbox Container App deployed
- **WHEN** infrastructure is provisioned via `azd up`
- **THEN** a separate Container App named `sandbox` is created with Docker-in-Docker support, pre-installed GitHub Copilot CLI, and inbound access restricted to the backend Container App only

#### Scenario: Sandbox exposes task API
- **WHEN** the sandbox Container App is running
- **THEN** it SHALL accept POST requests to `/tasks` with command payloads and stream CLI output via SSE on `/tasks/{id}/stream`

### Requirement: Sandbox lifecycle management
The system SHALL manage sandbox container lifecycle including creation, health monitoring, and recreation when skill configuration changes.

#### Scenario: Sandbox recreation on skill change
- **WHEN** a user installs or uninstalls a skill
- **THEN** the sandbox SHALL be flagged for recreation and a fresh sandbox SHALL be provisioned with the updated skill set before the next dev task execution

#### Scenario: Sandbox health check
- **WHEN** the backend attempts to delegate a task to the sandbox
- **THEN** it SHALL first verify sandbox health via a `/health` endpoint and recreate the sandbox if unhealthy

### Requirement: Skills synchronization
The system SHALL make the user's installed skills available inside the sandbox container at `/home/agent/.copilot/skills/`. Skills are synchronized at container build/restart time, not at runtime.

#### Scenario: Skills copied at sandbox creation
- **WHEN** a new sandbox container is started
- **THEN** all skills from the host `.agents/skills/` directory (local) or Blob Storage (Azure) SHALL be available at `/home/agent/.copilot/skills/`

#### Scenario: Skills refreshed on rebuild
- **WHEN** the sandbox container is rebuilt or restarted after new skills are installed
- **THEN** the updated skill set SHALL be available inside the container

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
