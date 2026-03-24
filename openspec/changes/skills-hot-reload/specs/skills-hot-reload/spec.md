## ADDED Requirements

### Requirement: Sandbox skill sync endpoint
The sandbox server SHALL expose a `POST /skills/sync` endpoint that triggers a full re-sync of all skills from Azure Blob Storage into `/home/agent/.copilot/skills/`.

#### Scenario: Sync triggered after skill activation
- **WHEN** the backend calls `POST /skills/sync` on the sandbox
- **THEN** the sandbox SHALL download all skill blobs from the `skills` container in blob storage
- **AND** write them to `/home/agent/.copilot/skills/<skill-name>/`
- **AND** return a JSON response with the count of skills synced

#### Scenario: Sync with no blob storage configured
- **WHEN** `POST /skills/sync` is called and `AZURE_STORAGE_ACCOUNT_NAME` is not set
- **THEN** the sandbox SHALL return a 200 response with `{"synced": 0, "message": "No storage account configured"}`

#### Scenario: Sync with blob storage unavailable
- **WHEN** `POST /skills/sync` is called and blob storage is unreachable
- **THEN** the sandbox SHALL return a 500 response with an error message
- **AND** existing skills on disk SHALL remain unchanged

### Requirement: Sandbox skill delete endpoint
The sandbox server SHALL expose a `DELETE /skills/:name` endpoint that removes a specific skill from `/home/agent/.copilot/skills/`.

#### Scenario: Skill deleted after deactivation
- **WHEN** the backend calls `DELETE /skills/my-skill` on the sandbox
- **THEN** the sandbox SHALL remove the directory `/home/agent/.copilot/skills/my-skill/`
- **AND** return a JSON response confirming deletion

#### Scenario: Deleting a non-existent skill
- **WHEN** `DELETE /skills/unknown-skill` is called and the skill directory does not exist
- **THEN** the sandbox SHALL return a 200 response (idempotent)

### Requirement: Backend pushes to sandbox on activation
The backend skill activation endpoint SHALL call the sandbox `POST /skills/sync` endpoint after uploading skill files to blob storage.

#### Scenario: Marketplace skill activated and pushed
- **WHEN** a user activates a marketplace skill via `POST /api/agents/skills/install`
- **AND** the skill files are uploaded to blob storage
- **THEN** the backend SHALL call `POST {SANDBOX_URL}/skills/sync` to trigger immediate availability
- **AND** if the sandbox call fails, the activation SHALL still succeed (best-effort push)

#### Scenario: Local skill uploaded and pushed
- **WHEN** a user uploads a local skill via `POST /api/dev/skills/upload-local`
- **AND** the files are written to blob storage
- **THEN** the backend SHALL call `POST {SANDBOX_URL}/skills/sync`

### Requirement: Backend removes from sandbox on deactivation
The backend skill deactivation endpoint SHALL call the sandbox `DELETE /skills/:name` endpoint after removing the skill from blob storage.

#### Scenario: Skill deactivated and removed from sandbox
- **WHEN** a user deactivates a skill via `DELETE /api/agents/skills/{name}`
- **THEN** the backend SHALL delete skill blobs from blob storage
- **AND** call `DELETE {SANDBOX_URL}/skills/{name}` to remove from running sandbox
- **AND** if the sandbox call fails, deactivation SHALL still succeed (best-effort)
