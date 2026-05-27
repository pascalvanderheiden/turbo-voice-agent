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
