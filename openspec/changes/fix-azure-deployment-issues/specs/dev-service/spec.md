## MODIFIED Requirements

### Requirement: Pipeline Execution
The dev-service SHALL execute pipeline stages (Plan → Build → Run → Test) as background tasks immediately after a dev task is created. The service SHALL log each stage transition with structured JSON including taskId, stage name, status, duration, and any error details. The service SHALL ensure background task execution is reliable in containerized environments (Azure Container Apps) by verifying the async event loop is active before spawning tasks.

#### Scenario: Pipeline stages kick off after task creation
- **WHEN** a dev task is created via `POST /api/dev`
- **THEN** the pipeline stages SHALL begin executing in the background within 1 second
- **AND** each stage transition SHALL be logged with a correlation ID

#### Scenario: Pipeline execution in production container environment
- **WHEN** a dev task is created in an Azure Container Apps deployment
- **THEN** the background task SHALL execute reliably regardless of container scaling events
- **AND** if the background task fails to spawn, the task status SHALL be set to "failed" with a descriptive error

### Requirement: Task CRUD Operations
The dev-service SHALL provide REST endpoints for creating, reading, listing, and deleting dev tasks. The `DELETE /api/dev/{id}` endpoint SHALL gracefully handle deletion of tasks in any status (pending, running, completed, failed) and SHALL clean up associated artifacts. Deletion errors SHALL be logged with the task ID and error details.

#### Scenario: Delete a running dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for a task with status "running"
- **THEN** the service SHALL cancel any in-progress pipeline stages
- **AND** remove the task record and associated artifacts
- **AND** return HTTP 200 with confirmation

#### Scenario: Delete a completed dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for a completed task
- **THEN** the service SHALL remove the task record and associated artifacts (screenshots, code archives)
- **AND** return HTTP 200 with confirmation

#### Scenario: Delete a non-existent dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for an ID that does not exist
- **THEN** the service SHALL return HTTP 404 with a descriptive error message
