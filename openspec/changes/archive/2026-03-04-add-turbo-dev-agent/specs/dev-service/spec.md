## ADDED Requirements

### Requirement: Development Task Storage
The system SHALL store development tasks with title, specId, status, stages, artifacts, and timestamps. Each task tracks a 4-stage pipeline: Plan, Build, Run, Test.

#### Scenario: Create development task manually
- **WHEN** a user creates a dev task with a title and optional specId
- **THEN** the system SHALL create a task with id, title, specId, status "pending", four stages each with status "pending", and timestamps
- **AND** return the created task with a unique ID

#### Scenario: Create development task from spec
- **WHEN** a user triggers a dev task from an existing spec
- **THEN** the system SHALL create a task linked to the spec via specId
- **AND** the task title SHALL default to the spec title if not provided

### Requirement: Development Task CRUD Operations
The system SHALL provide REST endpoints for managing development tasks.

#### Scenario: List all development tasks
- **WHEN** `GET /api/dev` is called
- **THEN** the system SHALL return all dev tasks ordered by creation date descending

#### Scenario: Get single development task
- **WHEN** `GET /api/dev/{id}` is called with a valid ID
- **THEN** the system SHALL return the full dev task including all stages, artifacts, and logs

#### Scenario: Delete development task
- **WHEN** `DELETE /api/dev/{id}` is called
- **THEN** the system SHALL remove the task and any associated artifact files from disk

### Requirement: Development Pipeline Execution
The system SHALL execute a 4-stage sequential pipeline as a background task: Plan → Build → Run → Test. Each stage updates status independently.

#### Scenario: Trigger pipeline
- **WHEN** `POST /api/dev/{id}/trigger` is called on a pending task
- **THEN** the system SHALL start the pipeline as an async background task
- **AND** immediately return the task with status "running"
- **AND** update stage statuses as each stage starts and completes

#### Scenario: Plan stage
- **WHEN** the Plan stage executes
- **THEN** the system SHALL use gpt-5.3-codex via the GitHub Copilot SDK to analyze the linked spec and produce an implementation plan
- **AND** store the plan as the stage output
- **AND** set the stage status to "completed"

#### Scenario: Build stage
- **WHEN** the Build stage executes after a successful Plan stage
- **THEN** the system SHALL use gpt-5.3-codex to generate a complete frontend application based on the plan
- **AND** write the generated code to a workspace directory
- **AND** run the build command (e.g., `npm run build`)
- **AND** set the stage status to "completed" if the build succeeds, or "failed" with error logs if it fails

#### Scenario: Run stage
- **WHEN** the Run stage executes after a successful Build stage
- **THEN** the system SHALL start the generated application's dev server
- **AND** verify the application is accessible on a local port
- **AND** set the stage status to "completed" if the server responds

#### Scenario: Test stage
- **WHEN** the Test stage executes after a successful Run stage
- **THEN** the system SHALL use Playwright MCP to navigate to the running application
- **AND** take accessibility snapshots and screenshots of key pages
- **AND** store screenshots as base64 artifacts on the task
- **AND** compress the source code into a .tar.gz archive stored in `.data/dev/`
- **AND** set the stage status to "completed"

#### Scenario: Pipeline failure
- **WHEN** any stage fails
- **THEN** the pipeline SHALL stop and mark the task status as "failed"
- **AND** the failed stage SHALL store error details
- **AND** subsequent stages SHALL remain in "pending" status

### Requirement: Development Task Artifacts
The system SHALL store and serve artifacts produced during pipeline execution.

#### Scenario: Screenshot artifacts
- **WHEN** the Test stage produces screenshots
- **THEN** screenshots SHALL be stored as base64-encoded data in the task's artifacts list
- **AND** each artifact SHALL have a name, type ("screenshot"), and data field

#### Scenario: Code archive artifact
- **WHEN** the Test stage completes successfully
- **THEN** the generated source code SHALL be compressed as a .tar.gz file
- **AND** stored in `.data/dev/{task_id}.tar.gz`
- **AND** a download endpoint `GET /api/dev/{id}/download` SHALL serve the archive

### Requirement: Development Task Persistence
The system SHALL persist dev tasks to JSON files for local development and to Cosmos DB when available.

#### Scenario: Data survives restart
- **WHEN** the backend restarts
- **THEN** previously created dev tasks are loaded from disk and available via API
