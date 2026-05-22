## Why

The current sandbox stack uses **two parallel implementations**: a long-running shared Container App (`ca-sandbox-*`) as a fallback, and per-task **Azure Container Instance (ACI)** container groups for isolation. Both have real problems:

- **ACI cold-start is slow** (~30–120s for ARM deploy + image pull), which delays every dev-task and forces "split provisioning" gymnastics in `aci_sandbox_service.py` to overlap startup with other work.
- **The shared Container App is not isolated** — a single noisy task can affect others, and the public hello-world placeholder image causes the recurring `Operation expired` provisioning failures we just fought through.
- **Two code paths** (`SANDBOX_URL` vs per-task IP) double the maintenance surface and the test matrix.
- **ACI infra is heavy**: dedicated VNet subnet with `Microsoft.ContainerInstance/containerGroups` delegation, NSG, user-assigned identity, ARM polling logic, orphan-cleanup loop.

**Azure Container Apps dynamic sessions** (GA feature on the platform we already deploy to) solves all of this: prewarmed pools deliver **subsecond** session allocation, Hyper-V isolation per session, automatic lifecycle/cooldown, and a simple `identifier`-based REST routing API. We get stronger isolation than ACI, faster cold-start than either option, and we delete the entire ACI module + Container App sandbox + fallback toggle.

## What Changes

- **Add** a `Microsoft.App/sessionPools` resource (custom container type) in Bicep, deployed inside the existing Container Apps Environment, using the existing sandbox image from ACR.
- **Add** a new `SessionSandboxService` in the backend that allocates sessions via the pool's management endpoint, using each dev-task ID as the session `identifier`.
- **Replace** all sandbox routing (`SANDBOX_URL` + per-task ACI IP resolution) with the session pool management URL + identifier query param. Backend code paths collapse to one.
- **BREAKING**: Remove the `USE_ACI_SANDBOX` feature flag and both backing implementations (shared Container App sandbox + per-task ACI). Dynamic sessions become the only sandbox runtime.
- **BREAKING**: Remove all ACI infrastructure — `aci-network.bicep` (subnet, NSG), `aci-identity.bicep` (user-assigned identity), `aci-backend-role.bicep` (RBAC), and `container-app-sandbox.bicep` (the shared CA).
- **BREAKING**: Remove `ACI_*` and `SANDBOX_URL` environment variables from the backend container app.
- **Delete** `aci_sandbox_service.py` and the orphan-cleanup background task.
- **Update** `sandbox_service.py` to track session pool state instead of Container App state in Cosmos DB (session ID, identifier, last activity).
- **Update** dev-task pipeline orchestration: `start_provisioning` / `wait_until_ready` collapse into a single call (sessions are prewarmed; no polling needed).
- **Update** docs (`docs/sandbox.md`, AGENTS.md sandbox section, README deployment) to describe dynamic sessions instead of ACI.

## Capabilities

### New Capabilities
- `dynamic-session-sandbox`: Per-task sandbox execution backed by a Container Apps session pool, replacing both shared Container App and per-task ACI. Covers session allocation, identifier routing, lifecycle, and skill availability inside sessions.
- `session-pool-infra`: Bicep infrastructure for the Container Apps session pool — pool resource, custom container image config, RBAC for backend → pool management endpoint, cooldown/scale settings.

### Modified Capabilities
- `aci-sandbox-infra`: All requirements **REMOVED** — ACI infrastructure (VNet subnet, identity, NSG, RBAC) is deleted.
- `aci-sandbox-lifecycle`: All requirements **REMOVED** — per-task ACI provisioning, IP resolution, and teardown are replaced by session allocation.
- `copilot-cli-sandbox`: Requirements updated — sandbox provisioning, lifecycle, and routing now describe session pools instead of Container App + ACI fallback; the `USE_ACI_SANDBOX` toggle is removed.
- `sandbox-auth`: `GH_TOKEN` injection moves from ACI environment variables to session-allocation request headers/env.
- `sandbox-skill-mount`: Skills sync remains identical (the session container is still our same image with the same entrypoint), but the "Azure skills downloaded at startup" scenario applies on session warmup instead of ACI startup.

## Impact

**Affected code:**
- `backend/app/services/sandbox_service.py` — schema change for tracked state (session ID + identifier replace `containerAppUrl` + per-task IP cache).
- `backend/app/services/aci_sandbox_service.py` — **deleted**.
- `backend/app/services/` — new `session_sandbox_service.py` (session allocation, identifier-based HTTP client).
- Anywhere `_sandbox_exec`, live-preview proxy, or file-download helpers resolve a URL — switch to `{poolManagementUrl}?identifier={taskId}` + path forwarding.
- `backend/app/main.py` — remove ACI service init, orphan-cleanup task, fallback-mode branching.

**Affected infrastructure:**
- `infra/modules/container-app-sandbox.bicep`, `aci-network.bicep`, `aci-identity.bicep`, `aci-backend-role.bicep` — **deleted**.
- `infra/main.bicep` — remove ACI module wiring, the sandbox CA module, the `enableAciSandbox` param, and ACI subnet/NSG references. Add `session-pool.bicep` module.
- `infra/scripts/collect-deployment-params.sh` — remove ACI-related prompts/env.
- `infra/main.parameters.json` — remove ACI/sandbox-CA params.

**Affected env vars (BREAKING removal):**
- `USE_ACI_SANDBOX`, `SANDBOX_URL`, `ACI_RESOURCE_GROUP`, `ACI_SUBNET_ID`, `ACI_IDENTITY_ID`, `ACI_IDENTITY_CLIENT_ID`, `ACI_ACR_LOGIN_SERVER`, `ACI_SANDBOX_IMAGE`, `ACI_SANDBOX_CPU`, `ACI_SANDBOX_MEMORY`, `ACI_SANDBOX_PORT`.
- **New**: `SESSION_POOL_MANAGEMENT_ENDPOINT`, `SESSION_POOL_NAME`.

**Affected dependencies:**
- Drop `azure-mgmt-containerinstance` from `backend/pyproject.toml`.
- Keep `azure-identity` (still needed for the session pool management endpoint auth).
- Add `azure-mgmt-app` (session pool ARM operations, if not already present).

**Regional availability**: Dynamic sessions are GA in our target regions (`eastus2`, `westeurope`, `northeurope`, `swedencentral`, etc.). No regional regression.

**Cost impact**: Net reduction — no idle Container App replicas, no per-task ARM deploys, no orphaned ACI groups. Billing shifts to session-pool consumption (CPU/memory while sessions are active + a small pool baseline).

**Migration**: Single deployment cycle. After `azd up`:
1. New session pool comes online.
2. Backend redeploys reading new env vars.
3. Old `ca-sandbox-*` and any lingering ACI groups can be manually deleted post-cutover (no in-flight tasks survive a deploy anyway).
