# Infrastructure (Bicep + azd)

Deploys the Turbo Voice Agent to Azure: backend & frontend Container Apps,
Cosmos DB, AI Foundry (multi-region), ACR, and the Azure Container Apps
**dynamic session pool** (`sp-sandbox-*`) that hosts per-task sandboxes.

```bash
azd auth login
azd up
```

## Layout

- `main.bicep` — top-level orchestrator
- `modules/session-pool.bicep` — dynamic session pool for sandbox execution
- `modules/session-pool-role.bicep` — backend → pool `Session Executor` role (deterministic GUID)
- `modules/container-app-{backend,frontend}.bicep` — public Container Apps
- `modules/rbac.bicep` — RBAC over ACR, Cosmos, Storage, AI Foundry
- `scripts/build-sandbox-image.sh` — builds the sandbox image into ACR as `turbo-voice-agent/sandbox:latest` (azd `postprovision` + `postdeploy` hook)
- `scripts/collect-deployment-params.sh` — interactive parameter collection
- `scripts/select-model-regions.sh` — quota-aware AI Foundry region picker
- `scripts/setup-entra-app.sh` — Entra app registration + redirect URIs

## Sandbox image

The sandbox is **not** an `azd` service — it has no Container App. The image is
built directly to ACR by `infra/scripts/build-sandbox-image.sh` (invoked by the
azd `postprovision` and `postdeploy` hooks). The session pool pulls
`${ACR}/turbo-voice-agent/sandbox:latest` at session-allocate time.

## Upgrading from the legacy ACI sandbox

Earlier deployments provisioned per-task `sandbox-*` Azure Container Instances
(ACI). The new architecture replaces them with the dynamic session pool. If you
are upgrading an existing environment:

1. Run `azd up` (or `azd provision`) — this creates the session pool and the
   RBAC the backend needs to talk to it.
2. Clean up leftover ACI container groups so they stop incurring cost:

   ```bash
   scripts/cleanup-aci-orphans.sh                       # interactive
   scripts/cleanup-aci-orphans.sh <resource-group>      # explicit RG
   scripts/cleanup-aci-orphans.sh --yes                 # non-interactive (CI)
   ```

   The script is idempotent — safe to run on fresh environments (no-op).

3. Confirm the backend env has `SESSION_POOL_MANAGEMENT_ENDPOINT` and
   `SESSION_POOL_NAME` set:

   ```bash
   az containerapp show -n ca-backend-<token> -g <rg> \
     --query "properties.template.containers[0].env[?name=='SESSION_POOL_MANAGEMENT_ENDPOINT']"
   ```

## RBAC notes

All role assignments use **deterministic GUIDs** (`guid(scope, principalId, roleDefId)`)
to avoid the `RoleAssignmentExists` collisions that occur when manual
`az role assignment create` calls are used to unstick provisioning. See
`.squad/skills/aca-provision-recovery/SKILL.md` for the full pattern.

## Troubleshooting

### `401` / `403` from the session pool

Symptom: backend logs `sandbox.session.error` with `status_code=401|403` immediately after a fresh deploy.

Cause: Azure RBAC propagation lag — `Azure ContainerApps Session Executor` role assignments can take **5–10 minutes** to become effective on a newly-created pool.

Verify the assignment exists:

```bash
BACKEND_MI=$(az containerapp show -n ca-backend-<token> -g <rg> \
  --query "identity.principalId" -o tsv)
POOL_ID=$(az resource show -n sp-sandbox-<token> -g <rg> \
  --resource-type Microsoft.App/sessionPools --query id -o tsv)
az role assignment list --assignee "$BACKEND_MI" --scope "$POOL_ID"
```

If the assignment is missing, re-run `azd provision`. If it's present but calls still 401, wait and retry — the client transparently retries once on 401/403 with a refreshed token, so persistent failures are an RBAC issue, not a token issue.

### `429` from the session pool

Symptom: `sandbox.session.error` with `status_code=429`.

Cause: `maxConcurrentSessions` exceeded — too many active dev-tasks for the pool's capacity.

Fix: increase `sessionPoolMaxConcurrent` in `infra/main.parameters.json` (or via `azd env set SESSION_POOL_MAX_CONCURRENT <n>`) and re-run `azd provision`. The Bicep parameter is plumbed through `infra/modules/session-pool.bicep`.

### Probe failures — sandbox container never becomes ready

Symptom: session allocation times out; pool logs show repeated readiness probe failures.

Cause: the sandbox image's `/ready` endpoint returns 503 until skill-sync completes and writes `/tmp/sandbox-state/skills-synced`. If the Blob Storage sync fails or the mount is missing, the marker never appears.

Diagnose:

```bash
# Tail container logs for the session pool (system logs of the latest session)
az monitor activity-log list --resource-id "$POOL_ID" --max-events 20
# Or pull recent stdout from the pool's container instances:
az containerapp session-pool show -n sp-sandbox-<token> -g <rg> --query "properties"
```

Look for `skill-sync` errors in the sandbox entrypoint output. Common cause: backend managed identity is missing `Storage Blob Data Reader` on the skills container.

### Cold start >5s

Symptom: first dev-task call hangs for 5–30s before responding.

Cause: pool exhausted of prewarmed sessions — new allocations must spin up a fresh sandbox.

Fix: raise `sessionPoolReadyInstances` (the prewarm count) in `infra/main.parameters.json`. Also check `cooldownPeriodInSeconds` — too aggressive a cooldown destroys idle sessions before users return, forcing cold allocations. Recommended: `ready=2`, `cooldown=300` for low-traffic dev environments; bump `ready` for production.

Observability: every allocation emits `sandbox.session.allocated` with `latency_ms`. Dashboards/alerts on `p95(latency_ms) > 5000` will catch this regression early.
