# Azure Container Apps Provision Recovery

**Confidence:** HIGH (validated by 3 consecutive recovery sessions on 2026-05-22; session-pool variant validated 2026-05-22 on sandbox-dynamic-sessions migration)  
**Last Updated:** 2026-05-22 14:35 UTC  
**Validation:** Successfully diagnosed and recovered from identical failures on backend, frontend, and sandbox Container Apps. Includes side-effect mitigation for manual RBAC fixes. Session-pool variant root-cause confirmed via ARM operation logs and role-assignment inspection.

## When to Use
- `azd up` or `azd provision` fails with "Operation expired" on Container App
- Container App stuck in "Failed" provisioning state with no revisions
- System logs show "Failed to construct registry secret" or ACR authentication 401 errors
- RBAC module didn't execute (check with `az deployment group show -g <rg> -n rbac`)

## Root Cause Pattern
**Bicep dependency ordering catch-22:**
1. Container App resource created with system-assigned managed identity
2. Container App tries to pull image from ACR using managed identity auth
3. ACR authentication fails (401) because RBAC module hasn't run yet
4. RBAC module depends on `containerApp.outputs.principalId`
5. Deployment fails before RBAC executes → no role assignments created

## Diagnosis Steps

### 1. Check Container App State
```bash
az containerapp list -g <resource-group> \
  --query "[].{name:name, state:properties.provisioningState, principalId:identity.principalId}" -o table
```

### 2. Check System Logs for ACR Auth Errors
```bash
az containerapp logs show -n <app-name> -g <resource-group> --type system --tail 50
```
Look for: `"Failed to construct registry secret for registry"` or `"ACR token exchange endpoint returned error status: 401"`

### 3. Verify Identity Has No Role Assignments
```bash
PRINCIPAL_ID="<principal-id-from-step-1>"
az role assignment list --assignee $PRINCIPAL_ID --all -o table
```
If output is empty → RBAC module never ran.

### 4. Verify RBAC Module Didn't Deploy
```bash
az deployment group show -g <resource-group> -n rbac 2>&1
```
If error: `"Deployment 'rbac' could not be found"` → confirms RBAC module was skipped.

### 5. Check ACR for Images
```bash
az acr repository list -n <acr-name> -o table
```
If empty → provisioning failed before `azd deploy` (which builds/pushes images).

## Recovery Steps

### Option A: Manual RBAC Fix + Re-provision (Recommended)

**Step 1:** Manually grant ACR Pull role
```bash
# Get ACR resource ID
ACR_ID=$(az acr show -n <acr-name> --query id -o tsv)

# Get Container App principal ID
PRINCIPAL_ID=$(az containerapp identity show -n <app-name> -g <resource-group> --query principalId -o tsv)

# Grant AcrPull role (ID: 7f951dda-4ed3-4680-a7ca-43fe172d538d)
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "7f951dda-4ed3-4680-a7ca-43fe172d538d" \
  --scope $ACR_ID
```

**Step 2:** Complete provisioning
```bash
azd provision  # Should succeed now that RBAC is fixed
```

**Step 3:** Deploy container images
```bash
azd deploy  # Builds and pushes images, updates Container Apps
```

## Side Effects & Prevention

### Role Assignment Collision (Manual Fix → Subsequent Provision)

**Problem:** After manually creating role assignments with `az role assignment create` to unstick provisioning, subsequent `azd provision` fails with `RoleAssignmentExists` errors.

**Root cause:**
- Manual `az role assignment create` uses **RANDOM GUIDs** for role assignment names (Azure CLI default)
- Bicep `rbac.bicep` module uses **DETERMINISTIC names** via `guid(scope, principalId, roleDefId)`
- Azure RBAC enforces uniqueness on `(principal, role, scope)` triple
- Bicep's attempt to create an assignment with its deterministic name fails because an assignment for the same triple ALREADY exists under a different name (the random GUID)

**Symptoms:**
```
ERROR: RoleAssignmentExists: The role assignment already exists. The ID of the existing role assignment is <guid>.
```

**Prevention Option 1 (Preferred):** Use deterministic GUID when manually creating role assignments

⚠️ **COMPLEX** — not recommended for emergency recovery:
```bash
# Calculate deterministic GUID (same as Bicep)
ASSIGNMENT_NAME=$(echo -n "${ACR_ID}${PRINCIPAL_ID}${ROLE_DEF_ID}" | sha256sum | cut -c 1-32 | sed 's/\(.\{8\}\)\(.\{4\}\)\(.\{4\}\)\(.\{4\}\)/\1-\2-\3-\4-/')

az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role $ROLE_DEF_ID \
  --scope $ACR_ID \
  --name $ASSIGNMENT_NAME
```

**Prevention Option 2 (Recommended):** Delete manual assignments before re-running provision

✅ **SIMPLE** — use this for recovery:
1. List existing role assignments to identify manual ones:
   ```bash
   az role assignment list --scope $ACR_ID --role AcrPull -o json
   ```
2. Delete manual assignments by their IDs (from error message or list output):
   ```bash
   az role assignment delete --ids <full-assignment-id-1> <full-assignment-id-2> ...
   ```
3. **IMMEDIATELY** run `azd provision` to recreate assignments with deterministic names
   - ⚠️ Container Apps temporarily lose ACR Pull access during this window
   - Running revisions don't need to re-pull (they're already running cached images)
   - New revisions will fail to provision until assignments are recreated

**When to apply:**
- After manually creating role assignments to unstick a failed Container App
- Before re-running `azd provision` or `azd up` if you previously applied manual RBAC fixes
- If you see `RoleAssignmentExists` errors during Bicep deployment

**Detection:**
- List all role assignments on ACR: `az role assignment list --scope <acr-scope> --role AcrPull`
- Manual assignments have random GUIDs (e.g., `4e7e6a5b-5438-4a64-9b8f-fbd38d63927e`)
- Bicep assignments have deterministic GUIDs calculated from scope + principal + role


### Option B: Delete Failed App + Full Re-provision

**Step 1:** Delete failed Container App
```bash
az containerapp delete -n <app-name> -g <resource-group> --yes
```

**Step 2:** Re-run provision (will recreate app)
```bash
azd provision
```
⚠️ **Still requires manual RBAC fix** if Bicep modules not updated.

### Option C: Nuclear Reset (Last Resort)
```bash
azd down --purge  # Deletes all resources
azd up            # Full redeploy
```
⚠️ **DESTRUCTIVE** — only use if Options A/B fail.

## Prevention (Bicep Refactor)

**Problem:** Current `infra/modules/rbac.bicep` is a single monolithic module that depends on all Container Apps being healthy.

**Solution:** Two-phase RBAC:

### Phase 1: ACR Pull Only (Immediate)
Create `infra/modules/rbac-acr-only.bicep`:
```bicep
@description('Backend Container App managed identity principal ID')
param backendPrincipalId string

@description('Frontend Container App managed identity principal ID')
param frontendPrincipalId string

@description('Sandbox Container App managed identity principal ID')
param sandboxPrincipalId string = ''

@description('ACR name')
param acrName string

var acrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrBackendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, backendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

resource acrFrontendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, frontendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: frontendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

resource acrSandboxRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(sandboxPrincipalId)) {
  name: guid(acr.id, sandboxPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: sandboxPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}
```

### Phase 2: Update main.bicep
```bicep
// Immediate ACR access — no health dependency
module acrRbac 'modules/rbac-acr-only.bicep' = {
  name: 'rbac-acr'
  scope: rg
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    sandboxPrincipalId: sandbox.outputs.principalId
    acrName: acr.outputs.name
  }
}

// Full RBAC — runs after ACR access exists
module rbac 'modules/rbac.bicep' = if (deployRbac) {
  name: 'rbac'
  scope: rg
  dependsOn: [acrRbac]  // Explicit ordering
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    cosmosAccountName: cosmos.outputs.name
    acrName: acr.outputs.name  // Keep for non-ACR roles
    storageAccountName: storage.outputs.name
    aiEastUs2Name: aiEastUs2.outputs.name
    aiWestUsName: aiWestUs.outputs.name
    aiCentralUsName: aiCentralUs.outputs.name
    sandboxPrincipalId: sandbox.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
  }
}
```

### Phase 3: Remove ACR Pull from rbac.bicep
In `infra/modules/rbac.bicep`, **delete lines 142-178** (ACR Pull assignments for backend/frontend/sandbox) since they're now in `rbac-acr-only.bicep`.

## Related Issues
- Container App revision provisioning timeout
- "Resource with this name already exists or is in a conflicting state"
- Managed identity authentication to ACR fails on first deploy
- **Session pool variant** — see next section

## Session Pool Variant: First-Deploy ACR Pull Race

**Confidence:** HIGH (validated 2026-05-22 — Pascal hit it on first `azd up` of sandbox-dynamic-sessions)

### Symptoms

- Outer error from `azd`:
  ```
  ERROR: A resource with this name already exists or is in a conflicting state.
  SessionPoolOperationError: Failed to provision session pool 'sp-sandbox-<token>'.
  Error details: pool group create/update failed with error: time out.
  ```
- `az deployment operation group list -g <rg> -n deploy-session-pool` shows the pool resource with `code: SessionPoolOperationError` and the timeout message.
- `az role assignment list --assignee <pool-system-mi-principalId> --all` returns **empty**.
- `az resource show ... --query properties.customContainerTemplate.registryCredentials` shows `identity: "system"`.
- The image **does** exist in ACR (`az acr repository show` returns a manifest). Image availability is a red herring — the postdeploy/postprovision hook built it. The pool just can't read it.

### Why the Container App recovery pattern doesn't apply

Container Apps tolerate "no ACR Pull yet" because revision provisioning is async — ARM marks the Container App `Succeeded` before the first pull, so the sibling role-assignment resource gets a chance to run, and a subsequent revision pulls successfully.

Session pools do **not** have this grace. The pool RP synchronously pulls during `PUT`. If the pull fails, the RP polls/retries internally and eventually returns "time out". The sibling role-assignment never executes because the pool reached terminal Failed state first.

### Root Cause

```
Bicep declares:
  resource sessionPool { identity: { type: 'SystemAssigned' } ... }
  resource acrPullRole { ... principalId: sessionPool.identity.principalId ... }

ARM execution:
  1. Create sessionPool shell → principalId allocated
  2. Pool starts pulling image (uses system MI = principalId)
  3. ACR returns 401 (no role assignment yet)
  4. Pool retries internally, eventually times out
  5. Pool resource → Failed
  6. acrPullRole resource → Skipped (parent dependency failed)
```

The sibling role assignment was never going to run in time.

### Recovery

1. **Delete the failed pool** so retry isn't blocked by name collision:
   ```bash
   az resource delete --ids /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.App/sessionPools/<pool-name>
   ```
   Takes ~1 minute. No `az containerapp sessionpool` CLI is required.

2. **Switch the pool to a pre-granted user-assigned MI.** This is the fix — apply the Bicep changes below, then `azd provision`.

### Prevention (Bicep)

**Module 1 — pre-granted UAMI** (`infra/modules/session-pool-identity.bicep`):

```bicep
param name string
param location string
param acrId string

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, uami.id, acrPullRoleId)   // deterministic — see Side Effects above
  scope: acr
  properties: {
    principalId: uami.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalType: 'ServicePrincipal'
  }
}

output id string = uami.id
output principalId string = uami.properties.principalId
```

**Module 2 — session pool** (`infra/modules/session-pool.bicep`, changed bits):

```bicep
param pullIdentityId string   // resource ID of the UAMI above
// ...
resource sessionPool 'Microsoft.App/sessionPools@2025-02-02-preview' = {
  // ...
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentityId}': {}
    }
  }
  properties: {
    customContainerTemplate: {
      // ...
      registryCredentials: {
        server: acrLoginServer
        identity: pullIdentityId   // resource ID, NOT 'system'
      }
    }
  }
}
```

Remove any inline `acrPullRole` resource that targets the pool's system MI — it can't help and confuses post-mortem readers.

**Module 3 — main.bicep ordering:**

```bicep
module sessionPoolIdentity 'modules/session-pool-identity.bicep' = {
  // params: name, location, acrId
}

module sessionPool 'modules/session-pool.bicep' = {
  params: {
    // ...
    pullIdentityId: sessionPoolIdentity.outputs.id
  }
}
```

The implicit `dependsOn` from the parameter reference is sufficient — ARM deploys identity (and the AcrPull assignment inside it) before the pool starts pulling.

### When to apply this pattern

Any ACA resource that **synchronously pulls during create** in a single ARM operation. Session pools today; likely future resource types with the same shape (prewarmed pools, replicas, etc.). If a resource has the "create + pull" combined, pre-grant a UAMI. Don't rely on a sibling role assignment to its system-assigned identity.

## Session Pool Variant: Stale Image Probe Mismatch (Postprovision Chicken-and-Egg)

**Confidence:** HIGH (validated 2026-05-22 — Pascal hit it immediately after the UAMI fix landed)

### Symptoms

- Outer error from `azd`:
  ```
  SessionPoolOperationError: Failed to provision session pool 'sp-sandbox-<token>'.
  Error details: pool group create/update failed with error: pool is in bad status
  because pods are crashing, crashing pods count: 0.
  ```
- The "crashing pods count: 0" wording is misleading — it does **not** mean zero failures. It means the pool currently has zero healthy pods and the RP has given up trying to start more. (Internally: pods are killed by the Liveness probe before they ever count as "running", so they never reach the "crashing" bucket.)
- `az resource show` on the pool: `provisioningState: Failed`, `nodeCount: 0`, UAMI is correctly attached and has AcrPull (so the previous variant is genuinely fixed).
- Image **does** exist in ACR — but its `createdTime` predates the commit that added the probe endpoints the pool is configured to hit.

### Root Cause

`build-sandbox-image.sh` is wired to azd `postprovision` and `postdeploy` hooks. When the pool fails during provision:
1. The pool resource fails.
2. `azd provision` aborts → `postprovision` hook never runs → image not rebuilt.
3. Next `azd provision` reuses the same stale `:latest` image.
4. Probes (`/health` Liveness 10s, `/ready` Startup 5s × 30) hit endpoints that don't exist in the stale image → 404 → pod killed by Liveness within ~30s → pool reports "pods crashing".
5. Loop repeats forever; nothing about the failure surfaces "stale image" — the user blames the pool config, the UAMI, the probes, anything but the image.

### Diagnosis Steps

```bash
# 1. Image creation timestamp
az acr repository show -n <acr-name> --image turbo-voice-agent/sandbox:latest \
  --query "{created:createdTime,digest:digest}" -o json

# 2. Last commit timestamp for sandbox/ files
git log -1 --pretty=format:"%ad" --date=iso-strict -- sandbox/

# 3. If git timestamp > image createdTime → image is stale → this is your failure mode.
```

### Recovery

1. **Rebuild the image directly** (do NOT wait for postprovision):
   ```bash
   bash infra/scripts/build-sandbox-image.sh
   ```
   `az acr build` runs server-side in ACR (~3 minutes). Overwrites `:latest`.

2. **Delete the failed pool** (so name collision doesn't block recreate):
   ```bash
   az resource delete --ids /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.App/sessionPools/<pool-name>
   ```

3. **Re-run** `azd provision`. The pool now pulls the fresh image, probes return 200, `nodeCount` climbs to `readySessionInstances`, deployment succeeds, postprovision finally runs (and rebuilds the image again — harmless idempotent no-op for that cycle).

### Prevention

Move the image build to **`preprovision`** in `azure.yaml`:

```yaml
hooks:
  preprovision:
    posix:
      run: |
        # ... existing param/region/entra scripts ...
        # Rebuild sandbox image BEFORE the pool tries to start.
        # No-op on first run (script exits 0 when AZURE_CONTAINER_REGISTRY is unset).
        bash infra/scripts/build-sandbox-image.sh
```

The script already exits 0 cleanly when ACR doesn't exist yet (first-ever run), so this is safe to add unconditionally. On every subsequent run, the image is rebuilt against the current `sandbox/` source before the pool is reconciled — eliminating the staleness window.

Keep `postprovision`/`postdeploy` invocations too: postprovision rebuilds with full env (in case preprovision was skipped), postdeploy refreshes on code-only changes.

### When to apply this pattern

Any ACA resource (or future resource type) that:
- Has health probes configured against application endpoints, AND
- Pulls a custom image at create time, AND
- Has the image build step wired to a hook that only runs on successful provision.

If you have a "image build → resource create → image rebuild" cycle where the rebuild only runs after success, you have this bug latent. Move at least one build invocation to a pre-resource-creation hook.

## References
- [Azure Container Apps Managed Identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [ACR authentication with Managed Identity](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication-managed-identity)
- [Bicep module dependencies](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/modules#module-dependencies)

## Session Pool Variant: Per-Task Config vs Container-Startup Config

**Confidence:** HIGH (validated 2026-05-22 — POST /tasks 400 on first dev-task after session pool migration; root cause traced in `sandbox/server.js` against backend dev_agent payload)

### The class of mistake

When migrating from a **per-user, per-task ACI container** (lived only for that user's task; baked credentials/skills at container start) to a **shared session-pool container** (ephemeral, reused across users, prewarmed before any user is known), every config item must be re-classified into one of two columns:

| Column | Description | Examples |
|--------|-------------|----------|
| **Container-startup config** | Identical for every user the container will ever serve | ACR image, model defaults, `PORT`, system packages, az login via UAMI |
| **Per-task config** | Specific to the user/task currently being served | GitHub PAT, user-uploaded skills, per-task workspace state, OAuth tokens for the user's own integrations |

Anything in column 2 **cannot** be baked at container startup — the container doesn't know who it will serve yet. It must be delivered per-task by the backend, typically via:
- A header on the first request (e.g., `X-GH-Token` → middleware authenticates `gh` CLI in-process)
- A dedicated handshake endpoint the backend calls before submitting work (e.g., `POST /skills/sync` after the user's identity is known)
- A field in the work-submission body

### Symptom pattern

- Session pool allocation succeeds (fast — UAMI ACR Pull pre-grant is correct).
- The very first work-submission request (`POST /tasks`, `POST /jobs`, etc.) returns **400** or **403** complaining about missing credentials.
- The container has the auth state — it was set up by the new per-task path — but a **stale validation gate** in the route still checks for the old container-startup path (env var, file on disk, etc.) and refuses the request.

### Specific instance — POST /tasks 400 after X-GH-Token middleware

**The bug:** Phase 5 added an `X-GH-Token` request middleware that runs `gh auth login --with-token` and flips `ghAuthenticated = true`. But the `POST /tasks` route's validation still required `effectiveToken = req.body.ghToken || process.env.GH_TOKEN`. In a session pool:
- `process.env.GH_TOKEN` is unset (it was the docker-compose path).
- Backend sends the token via header only, never in the body.
- → 400 "GitHub token required" even though `gh` is fully authenticated.

**The fix** (`sandbox/server.js`):
```js
// Before
if (prompt && !effectiveToken) { return res.status(400).json({ error: "..." }); }

// After
if (prompt && !effectiveToken && !ghAuthenticated) { return res.status(400).json({ error: "..." }); }
```

The spawned `copilot` CLI reads auth state from `gh`, so an authenticated gh state is sufficient. The existing `...(effectiveToken ? { GH_TOKEN: effectiveToken } : {})` env-injection already gracefully handles the no-env-var case.

### Diagnosis checklist when you hit this class of bug

When a session-pool container rejects a request the backend "obviously" satisfies:

1. **List every route-level validation in the container** — `grep -n "return res.status(40[0-9])" sandbox/server.js` (or equivalent).
2. **For each gate**, ask: *what config source does this check?* Env var? Disk file? Request body? Process state set by middleware?
3. **For each config source**, ask: *who sets this in a session pool?* If the answer is "the docker-compose entrypoint" or "the old ACI postdeploy script", that gate is stale.
4. **Cross-reference the backend's request shape.** Pull the actual payload from the backend client (e.g., `dev_agent.py` `_sandbox_exec`) and the actual headers. Compare to what each gate checks.
5. **Mismatch = stale gate.** Either teach the gate about the new path (e.g., accept process state), or have the backend send both.

### Diagnosis steps (read-only — no deploy needed)

```bash
# 1. Find all 400/403 gates in the sandbox route handlers.
grep -n "status(40[0-9])" sandbox/server.js

# 2. For each gate, identify the config source.
#    Look at the variable names: process.env.X, req.body.X, req.get('X-…'),
#    module-level state flipped by middleware.

# 3. Confirm what the backend sends. For Python httpx clients:
grep -nA8 "POST.*\"/tasks\"\|/skills/sync\|/files" backend/app/agents/*.py backend/app/services/*.py

# 4. Check pool container env from Bicep:
grep -nA3 "env: \[" infra/modules/session-pool.bicep
```

### Prevention

When adding new auth/config paths during a session-pool migration:

1. **Update ALL validation gates that protect the same capability**, not just the new entry point. A gate that checks for `req.body.token` must also accept `ghAuthenticated === true` (or whatever module-level state the new middleware sets).
2. **Add a contract test**: send a request with the new path (header) and no legacy path (no env var, no body field) and assert 2xx, not 4xx.
3. **Document the path** in a comment on the validation gate so the next migrator sees both branches.
4. **Distinguish "container has the credential" from "request supplied the credential"** in route logic. They are not equivalent in a session pool: the container can have a credential set by a *previous* request from a *previous* user — which is fine for `gh` auth (idempotent per session) but would be a leak for per-user secrets. Make this distinction explicit.

### When to apply this pattern

Any time you migrate a per-user container to a shared pool, audit every input the container accepted at startup (env vars, mounted secrets, command-line args) and decide whether it's column 1 (still OK at startup) or column 2 (must move to per-task delivery). The route handlers must reflect column 2 as a valid alternative to column 1, not as a mutually exclusive replacement during the transition.

