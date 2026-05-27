## ADDED Requirements

### Requirement: Single sandbox runtime backed by dynamic sessions
The backend SHALL use Azure Container Apps dynamic sessions as the sole sandbox runtime for dev-tasks. There SHALL NOT be any feature flag toggling between ACI, shared Container App, or sessions in deployed environments.

#### Scenario: Backend resolves sandbox via session pool only
- **WHEN** the backend deploys with `SESSION_POOL_MANAGEMENT_ENDPOINT` set
- **THEN** all sandbox HTTP calls SHALL route through the session pool management endpoint
- **AND** no code path SHALL reach the previous ACI or shared Container App implementations

#### Scenario: Local dev falls back to direct sandbox container
- **WHEN** the backend runs locally and `SESSION_POOL_MANAGEMENT_ENDPOINT` is unset
- **THEN** sandbox calls SHALL go directly to `http://sandbox:3000` (docker-compose service)
- **AND** no session allocation SHALL be attempted

### Requirement: Session allocation by dev-task identifier
The backend SHALL allocate a sandbox session by using the dev-task UUID as the session `identifier` query parameter. Subsequent requests for the same dev-task SHALL reuse the same session by reusing the identifier.

#### Scenario: First sandbox call for a task allocates a session
- **WHEN** the first sandbox HTTP call is made for dev-task `T`
- **THEN** the request URL SHALL include `?identifier={T}&api-version=2025-02-02-preview`
- **AND** the session pool SHALL allocate a prewarmed session and forward the request to it

#### Scenario: Subsequent calls reuse the same session
- **WHEN** any additional sandbox HTTP call is made for the same dev-task `T` before cooldown
- **THEN** the request SHALL use the same identifier
- **AND** the session pool SHALL route to the already-allocated session for `T`

#### Scenario: Different tasks get isolated sessions
- **WHEN** two dev-tasks `T1` and `T2` execute concurrently
- **THEN** they SHALL be routed to separate sessions with Hyper-V isolation between them

### Requirement: Path-forwarding HTTP client
The backend SHALL provide a `SessionSandboxClient` that wraps `httpx.AsyncClient`, prepends the pool management endpoint, attaches the Bearer token from `DefaultAzureCredential`, and injects `identifier` and `api-version` query parameters. Callers SHALL pass logical paths (`/tasks`, `/tasks/{id}/stream`, `/files/...`, `/skills/sync`, `/health`) unchanged.

#### Scenario: Caller path is forwarded to session container
- **WHEN** a caller invokes `client.post("/tasks", json=payload)` for dev-task `T`
- **THEN** the actual request URL SHALL be `{poolManagementEndpoint}/tasks?identifier={T}&api-version=2025-02-02-preview`
- **AND** the path `/tasks` SHALL be forwarded to the session container's port 3000

#### Scenario: SSE streaming endpoint
- **WHEN** a caller streams from `/tasks/{id}/stream`
- **THEN** the client SHALL preserve `Accept: text/event-stream` and HTTP/1.1 transport
- **AND** events SHALL be yielded to the caller as they arrive from the session container

#### Scenario: Authentication failure
- **WHEN** the pool management endpoint returns 401/403
- **THEN** the client SHALL refresh the token and retry once
- **AND** if the retry also fails, raise an authentication error

### Requirement: Session lifecycle managed by pool
The backend SHALL NOT explicitly create, delete, or poll session resources for lifecycle. The session pool SHALL allocate sessions on first request and SHALL destroy them after the configured cooldown period of inactivity.

#### Scenario: Session destroyed after cooldown
- **WHEN** no requests are made to a session for the configured cooldown period
- **THEN** the session pool SHALL destroy the session automatically
- **AND** the backend SHALL NOT take any action to delete it

#### Scenario: Backend explicitly stops a session on task cancellation
- **WHEN** a user cancels or deletes an in-flight dev-task
- **THEN** the backend SHALL POST `/.management/stopSession?identifier={T}` to release resources immediately
- **AND** SHALL tolerate a 404 response (session already gone)

#### Scenario: No orphan-cleanup background job
- **WHEN** the backend application starts
- **THEN** there SHALL NOT be a background task scanning for orphaned sandbox resources

### Requirement: Sandbox state schema reflects session identifier
The `SandboxState` model in Cosmos DB SHALL record `sessionIdentifier` (string) instead of `containerAppUrl`. The state SHALL track `status`, `sessionIdentifier`, `lastActivity`, and ownership metadata. Any per-task IP cache SHALL be removed.

#### Scenario: State stored after allocation
- **WHEN** a session is first allocated for dev-task `T`
- **THEN** the Cosmos `sandbox_state` document for `T` SHALL contain `sessionIdentifier = T` and `status = "active"`
- **AND** SHALL NOT contain `containerAppUrl`

#### Scenario: State cleared after cancellation
- **WHEN** the backend explicitly stops a session
- **THEN** the document SHALL be updated to `status = "stopped"`

### Requirement: Skill availability inside session
The session container SHALL synchronize skills from Azure Blob Storage during its startup (warm-up) phase, identical to the existing entrypoint behavior. Hot-reload via `/skills/sync` SHALL continue to be supported during the session's active lifetime.

#### Scenario: Skills present on first request
- **WHEN** the first request to a newly-allocated session calls `GET /skills`
- **THEN** the user's installed skills SHALL be listed
- **AND** they SHALL have been downloaded during session warm-up, not on request

#### Scenario: Skills hot-reloaded mid-session
- **WHEN** the user installs a new skill while a session is active
- **THEN** the backend SHALL POST `/skills/sync` to the session
- **AND** the new skill SHALL be available within seconds without session restart
