## MODIFIED Requirements

### Requirement: Skills synchronization
The system SHALL make the user's installed skills available inside the sandbox container at `/home/agent/.copilot/skills/`. Skills are synchronized at container build/restart time, not at runtime.

#### Scenario: Skills copied at sandbox creation
- **WHEN** a new sandbox container is started
- **THEN** all skills from the host `.agents/skills/` directory (local) or Blob Storage (Azure) SHALL be available at `/home/agent/.copilot/skills/`

#### Scenario: Skills refreshed on rebuild
- **WHEN** the sandbox container is rebuilt or restarted after new skills are installed
- **THEN** the updated skill set SHALL be available inside the container
