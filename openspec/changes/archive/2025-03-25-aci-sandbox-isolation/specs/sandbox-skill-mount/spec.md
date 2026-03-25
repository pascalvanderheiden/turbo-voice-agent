## MODIFIED Requirements

### Requirement: Azure skills downloaded from Blob Storage at startup
When running in ACI mode, skills SHALL be downloaded from Blob Storage during container startup via `sync-skills.sh` (same as current behavior). The hot-reload endpoint (`POST /skills/sync`) SHALL remain functional but is not expected to be called mid-task since each container is single-use.

#### Scenario: Skills available at container start in ACI
- **WHEN** an ACI sandbox container starts with `AZURE_STORAGE_ACCOUNT_NAME` set
- **THEN** `sync-skills.sh` downloads all skills from Blob Storage before the Express server starts accepting requests

#### Scenario: New skills available on next task
- **WHEN** a user activates a new skill in the marketplace
- **THEN** the skill is uploaded to Blob Storage and the next ACI container provisioned will include it at startup

#### Scenario: Hot-reload still works for Container App fallback
- **WHEN** `USE_ACI_SANDBOX=false` and the backend calls `POST /skills/sync` on the shared Container App
- **THEN** skills are synced from Blob Storage as before
