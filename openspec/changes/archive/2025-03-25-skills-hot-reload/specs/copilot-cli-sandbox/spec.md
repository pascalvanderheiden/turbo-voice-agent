## MODIFIED Requirements

### Requirement: Skills synchronization
The system SHALL make the user's installed skills available inside the sandbox container at `/home/agent/.copilot/skills/`. Skills are synchronized at container startup via the entrypoint script and hot-reloaded at runtime via the sandbox `/skills/sync` endpoint. Dev-task pipelines SHALL NOT include a skills installation stage.

#### Scenario: Skills copied at sandbox creation
- **WHEN** a new sandbox container is started
- **THEN** all skills from the host `.agents/skills/` directory (local) or Blob Storage (Azure) SHALL be available at `/home/agent/.copilot/skills/`

#### Scenario: Skills refreshed on rebuild
- **WHEN** the sandbox container is rebuilt or restarted after new skills are installed
- **THEN** the updated skill set SHALL be available inside the container

#### Scenario: No skills installation during dev-task pipeline
- **WHEN** a dev-task pipeline starts (mockup, sequential, or slides mode)
- **THEN** the pipeline SHALL NOT include a "skills" stage
- **AND** the pipeline SHALL NOT call `_install_skills_in_sandbox()` or `_verify_skills_in_sandbox()`
- **AND** skills SHALL already be present from startup sync or hot-reload

## REMOVED Requirements

### Requirement: Per-task skill verification via Copilot CLI
**Reason**: Skills are pre-loaded via startup sync and hot-reload. The verification prompt ("What skills do you have?") wasted a premium Copilot request per task and added ~15s latency.
**Migration**: Remove `_verify_skills_in_sandbox()` method. Skills are verified by the sync endpoint returning a count.
