### Requirement: Skills directory exists in sandbox container
The sandbox Docker image SHALL include an empty `/home/agent/.copilot/skills/` directory owned by the `agent` user.

#### Scenario: Fresh sandbox build with no skills installed
- **WHEN** the sandbox container is built with no skills in `.agents/skills/`
- **THEN** the directory `/home/agent/.copilot/skills/` SHALL exist and be writable by the `agent` user

### Requirement: Local dev skills mounted via Docker Compose
The Docker Compose sandbox service SHALL bind-mount the host `.agents/skills/` directory to `/home/agent/.copilot/skills/` in read-only mode.

#### Scenario: Skills available after container restart
- **WHEN** a user installs a skill via the backend skill management UI
- **AND** the sandbox container is restarted
- **THEN** the installed skill SHALL be visible at `/home/agent/.copilot/skills/<skill-name>/`

#### Scenario: No skills installed
- **WHEN** no skills have been installed and `.agents/skills/` is empty or missing
- **THEN** the sandbox SHALL start normally with an empty skills directory

### Requirement: Azure skills downloaded from Blob Storage at startup
When `AZURE_STORAGE_ACCOUNT_NAME` is set, the sandbox entrypoint SHALL download skills from the `skills` blob container into `/home/agent/.copilot/skills/` before starting the server. Additionally, skills SHALL be hot-reloaded at runtime via the `/skills/sync` endpoint without requiring a container restart.

#### Scenario: Skills downloaded on container start in Azure
- **WHEN** the sandbox container starts in Azure with `AZURE_STORAGE_ACCOUNT_NAME` set
- **THEN** the entrypoint SHALL download all skill blobs into `/home/agent/.copilot/skills/`
- **AND** the Copilot CLI SHALL have access to the downloaded skills

#### Scenario: Blob Storage unavailable at startup
- **WHEN** the sandbox container starts and Blob Storage is unreachable
- **THEN** the entrypoint SHALL log a warning and continue starting the server without custom skills

#### Scenario: Skill activated after container start
- **WHEN** a user activates a new skill while the sandbox container is already running
- **THEN** the backend SHALL trigger a `/skills/sync` call to the sandbox
- **AND** the skill SHALL be available in `/home/agent/.copilot/skills/` within seconds
- **AND** no container restart SHALL be required
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
