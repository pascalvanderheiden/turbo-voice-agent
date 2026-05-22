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
