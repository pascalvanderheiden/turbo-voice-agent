## ADDED Requirements

### Requirement: ACI container group provisioning
The backend SHALL create a new Azure Container Instance container group for each dev-task when the pipeline starts. The container group name SHALL follow the pattern `sandbox-{first 8 chars of task UUID}`. The container SHALL use the sandbox Docker image from ACR with the user-assigned managed identity for authentication.

#### Scenario: Successful provisioning on task start
- **WHEN** a dev-task pipeline begins execution
- **THEN** the backend creates an ACI container group in the configured resource group and subnet, using the latest sandbox image from ACR

#### Scenario: Container group becomes ready
- **WHEN** the ACI container group provisioning state becomes "Succeeded" and the sandbox health endpoint returns 200
- **THEN** the backend records the container's private IP and proceeds with the pipeline init stage

#### Scenario: Provisioning timeout
- **WHEN** the ACI container group does not reach "Succeeded" state within 120 seconds
- **THEN** the backend marks the dev-task as failed with error "Sandbox provisioning timed out" and deletes the container group

### Requirement: Per-task sandbox URL resolution
The backend SHALL resolve the sandbox URL dynamically for each dev-task by looking up the ACI container group's private IP address. All sandbox HTTP calls (`_sandbox_exec`, file downloads, live preview proxy) SHALL use this per-task URL instead of a static `SANDBOX_URL` environment variable.

#### Scenario: Sandbox exec uses per-task URL
- **WHEN** `_sandbox_exec` is called for a dev-task
- **THEN** it resolves the sandbox URL from the ACI container group's private IP on port 3000

#### Scenario: Live preview proxy routes to correct container
- **WHEN** a user opens live preview for a slides dev-task
- **THEN** the backend proxies requests to the ACI container assigned to that specific task

### Requirement: ACI container group teardown
The backend SHALL delete the ACI container group when a dev-task pipeline completes (success or failure) or when a dev-task is deleted by the user.

#### Scenario: Cleanup on pipeline completion
- **WHEN** a dev-task pipeline finishes (status becomes "completed" or "failed")
- **THEN** the backend deletes the associated ACI container group within 30 seconds

#### Scenario: Cleanup on task deletion
- **WHEN** a user deletes a dev-task that has an active ACI container group
- **THEN** the backend deletes the ACI container group before removing the task record

#### Scenario: Graceful handling of deletion failure
- **WHEN** ACI container group deletion fails (e.g., already deleted, transient error)
- **THEN** the backend logs a warning and continues; the orphan cleanup job will handle it

### Requirement: Orphaned container group cleanup
The backend SHALL run a background cleanup job that deletes ACI container groups older than 2 hours that are not associated with an active dev-task.

#### Scenario: Cleanup sweeps orphaned containers
- **WHEN** the cleanup job runs (every 15 minutes)
- **THEN** it lists all ACI container groups matching the `sandbox-*` name pattern, compares against active dev-tasks, and deletes any that have been running for more than 2 hours without an active task

#### Scenario: Active containers are not deleted
- **WHEN** the cleanup job finds a container group associated with a running dev-task
- **THEN** it skips that container group regardless of its age

### Requirement: Feature flag for ACI vs Container App sandbox
The backend SHALL support a `USE_ACI_SANDBOX` environment variable. When set to `true`, dev-tasks use ACI per-task isolation. When `false` or unset, the existing shared Container App sandbox is used.

#### Scenario: Feature flag enabled
- **WHEN** `USE_ACI_SANDBOX=true` is set in the backend environment
- **THEN** all new dev-tasks provision ACI container groups

#### Scenario: Feature flag disabled (default)
- **WHEN** `USE_ACI_SANDBOX` is not set or is `false`
- **THEN** all dev-tasks use the shared Container App sandbox via `SANDBOX_URL`
## REMOVED Requirements

### Requirement: ACI container group provisioning
**Reason**: Per-task ACI provisioning is replaced by session allocation from a prewarmed pool. ARM-based container group creation is no longer used.
**Migration**: Delete `aci_sandbox_service.py`. Replace all callers with the new `SessionSandboxClient` defined in `dynamic-session-sandbox`. Session allocation happens implicitly on the first HTTP request bearing the task UUID as `identifier`.

### Requirement: Per-task sandbox URL resolution
**Reason**: Sessions are routed by `identifier` query parameter against a single pool management endpoint — there is no per-task IP to resolve.
**Migration**: Replace dynamic IP lookups with the pool management URL + identifier. See `dynamic-session-sandbox` → "Path-forwarding HTTP client".

### Requirement: ACI container group teardown
**Reason**: The session pool destroys sessions automatically after a cooldown period of inactivity. Explicit teardown is unnecessary for the happy path; cancellation calls `stopSession` instead.
**Migration**: Replace the teardown logic with a single optional `POST /.management/stopSession?identifier={T}` on user cancellation. Remove `delete_container_group` and related polling.

### Requirement: Orphaned container group cleanup
**Reason**: With session pools, there are no orphaned ARM resources to clean up — sessions are pool-managed and destroyed on cooldown. The background cleanup task is no longer needed.
**Migration**: Delete the cleanup background task in `main.py`. One-time post-deploy script `scripts/cleanup-aci-orphans.sh` removes any leftover `sandbox-*` ACI groups from the previous regime, then deletes itself.

### Requirement: Feature flag for ACI vs Container App sandbox
**Reason**: Both backends are removed. Dynamic sessions are the only runtime in deployed environments; local dev uses the docker-compose sandbox via service discovery. No toggle exists.
**Migration**: Remove `USE_ACI_SANDBOX` from backend env, Bicep parameters, docs, and deployment scripts. Backend detects local vs cloud by presence/absence of `SESSION_POOL_MANAGEMENT_ENDPOINT`.
