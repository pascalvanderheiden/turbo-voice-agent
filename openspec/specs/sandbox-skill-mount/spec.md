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
When `AZURE_STORAGE_ACCOUNT_NAME` is set, the sandbox entrypoint SHALL download skills from the `skills` blob container into `/home/agent/.copilot/skills/` before starting the server. In ACI mode, skills are downloaded once at container start (each container is single-use). In Container App mode, skills are also hot-reloaded at runtime via the `/skills/sync` endpoint.

#### Scenario: Skills available at container start in ACI
- **WHEN** an ACI sandbox container starts with `AZURE_STORAGE_ACCOUNT_NAME` set
- **THEN** `sync-skills.sh` downloads all skills from Blob Storage before the Express server starts accepting requests

#### Scenario: New skills available on next task
- **WHEN** a user activates a new skill in the marketplace
- **THEN** the skill is uploaded to Blob Storage and the next ACI container provisioned will include it at startup

#### Scenario: Blob Storage unavailable at startup
- **WHEN** the sandbox container starts and Blob Storage is unreachable
- **THEN** the entrypoint SHALL log a warning and continue starting the server without custom skills

#### Scenario: Hot-reload still works for Container App fallback
- **WHEN** `USE_ACI_SANDBOX=false` and the backend calls `POST /skills/sync` on the shared Container App
- **THEN** skills are synced from Blob Storage as before
