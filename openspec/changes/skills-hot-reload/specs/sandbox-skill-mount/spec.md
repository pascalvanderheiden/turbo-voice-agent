## MODIFIED Requirements

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
