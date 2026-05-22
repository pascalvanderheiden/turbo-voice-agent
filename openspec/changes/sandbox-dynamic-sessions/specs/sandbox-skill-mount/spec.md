## MODIFIED Requirements

### Requirement: Azure skills downloaded from Blob Storage at startup
When `AZURE_STORAGE_ACCOUNT_NAME` is set, the sandbox entrypoint SHALL download skills from the `skills` blob container into `/home/agent/.copilot/skills/` before the container reports ready (Startup probe). For session-pool deployments, this download happens during **session warm-up** (before the session is added to the prewarmed pool), so allocated sessions already have the latest skills. Skills SHALL be hot-reloaded at runtime via the `/skills/sync` endpoint without requiring a session restart.

#### Scenario: Skills downloaded during session warm-up
- **WHEN** the session pool warms a new session instance
- **THEN** the entrypoint SHALL download all skill blobs into `/home/agent/.copilot/skills/`
- **AND** `GET /ready` SHALL only return 200 once the download completes
- **AND** the session SHALL be added to the prewarmed pool only after `/ready` succeeds

#### Scenario: Allocated session has skills on first request
- **WHEN** a request allocates a prewarmed session for dev-task `T`
- **THEN** the user's skills SHALL already be present in `/home/agent/.copilot/skills/`
- **AND** no skills download SHALL happen on the request path

#### Scenario: Blob Storage unavailable at warm-up
- **WHEN** a session warm-up runs and Blob Storage is unreachable
- **THEN** the entrypoint SHALL log a warning and continue
- **AND** the session SHALL still pass `/ready` so the pool does not stall
- **AND** the user MAY trigger `/skills/sync` later to retry

#### Scenario: Skill activated after session allocation
- **WHEN** a user activates a new skill while a session is allocated to their dev-task
- **THEN** the backend SHALL trigger a `/skills/sync` call to that session
- **AND** the skill SHALL be available in `/home/agent/.copilot/skills/` within seconds
- **AND** no session restart SHALL be required
