## ADDED Requirements

### Requirement: Structured Logging
All backend services SHALL implement structured JSON logging with consistent field names. Every log entry SHALL include: timestamp (ISO 8601), level (DEBUG/INFO/WARNING/ERROR), service name, correlation ID, and message. Request-scoped correlation IDs SHALL be propagated across all service calls within a single user request.

#### Scenario: API request logging
- **WHEN** an API request is received
- **THEN** the service SHALL log the request method, path, userId, and a generated correlation ID
- **AND** the response SHALL be logged with status code, duration in milliseconds, and the same correlation ID

#### Scenario: Pipeline stage logging
- **WHEN** a dev task pipeline stage executes
- **THEN** each stage transition SHALL be logged with taskId, stage name, status (started/completed/failed), duration, and correlation ID
- **AND** failures SHALL include the error message and stack trace

#### Scenario: Skill operation logging
- **WHEN** a skill is installed, deleted, or searched
- **THEN** the operation SHALL be logged with userId, skill name, operation type, and result (success/failure)

### Requirement: Distributed Tracing
The backend SHALL integrate with Azure Application Insights via the OpenTelemetry Python SDK. All HTTP requests, database operations (Cosmos DB), and external API calls (AI Foundry, Copilot SDK) SHALL be instrumented with distributed traces. Traces SHALL be queryable in the Azure Portal for end-to-end request visualization.

#### Scenario: End-to-end trace for dev task creation
- **WHEN** a user creates a dev task that triggers pipeline execution
- **THEN** a single distributed trace SHALL capture the API request, task creation in Cosmos DB, and all pipeline stage executions
- **AND** the trace SHALL be visible in Azure Application Insights

#### Scenario: Error trace with context
- **WHEN** a backend operation fails (e.g., pipeline stage, skill install, spec generation)
- **THEN** the error SHALL be captured in Application Insights with full context: userId, operation type, input parameters, and stack trace
- **AND** the error SHALL be correlated with the originating user request

### Requirement: Health and Diagnostic Endpoints
The backend SHALL expose a health check endpoint at `GET /api/health` that returns service status, dependency connectivity (Cosmos DB, Blob Storage, AI Foundry), and version information. This endpoint SHALL be used by Azure Container Apps health probes.

#### Scenario: Health check with all dependencies healthy
- **WHEN** `GET /api/health` is called and all dependencies are reachable
- **THEN** the response SHALL return HTTP 200 with status "healthy" and dependency statuses

#### Scenario: Health check with degraded dependency
- **WHEN** `GET /api/health` is called and a dependency (e.g., Cosmos DB) is unreachable
- **THEN** the response SHALL return HTTP 503 with status "degraded" and identify the failing dependency
