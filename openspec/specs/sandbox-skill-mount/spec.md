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
When `AZURE_STORAGE_ACCOUNT_NAME` is set, the sandbox entrypoint SHALL download skills from the `skills` blob container into `/home/agent/.copilot/skills/` before starting the server.

#### Scenario: Skills downloaded on container start in Azure
- **WHEN** the sandbox container starts in Azure with `AZURE_STORAGE_ACCOUNT_NAME` set
- **THEN** the entrypoint SHALL download all skill blobs into `/home/agent/.copilot/skills/`
- **AND** the Copilot CLI SHALL have access to the downloaded skills

#### Scenario: Blob Storage unavailable
- **WHEN** the sandbox container starts and Blob Storage is unreachable
- **THEN** the entrypoint SHALL log a warning and continue starting the server without custom skills
