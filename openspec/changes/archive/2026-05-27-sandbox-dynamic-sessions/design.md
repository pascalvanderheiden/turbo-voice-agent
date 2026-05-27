## Context

Today the sandbox runtime has two backends behind the `USE_ACI_SANDBOX` flag:

1. **Shared Container App** (`ca-sandbox-*`) — long-running, accessed via `SANDBOX_URL`. No per-task isolation; the placeholder hello-world image (port 80) vs ingress targetPort 3000 has caused repeated provisioning timeouts.
2. **Per-task Azure Container Instances** — `aci_sandbox_service.py` provisions a `Microsoft.ContainerInstance/containerGroups` per dev-task in a delegated VNet subnet. ARM deploy + image pull dominates startup (30–120s), which we mitigate with a split `start_provisioning` / `wait_until_ready` API that overlaps with other pipeline work. Requires its own subnet, NSG, user-assigned identity, RBAC, and orphan-cleanup loop.

Both share the same sandbox container image (`sandbox/Dockerfile`) and entrypoint that pulls skills from Azure Blob Storage at startup.

**Azure Container Apps dynamic sessions** is a platform feature on our existing Container Apps Environment. It exposes a **session pool** that prewarms containers and allocates them in milliseconds by a caller-provided `identifier`. Sessions get Hyper-V isolation. The pool manages lifecycle (cooldown → automatic destroy). The session API is REST-only — no ARM round-trips per task. The custom-container session pool resource (`Microsoft.App/sessionPools` with `containerType: CustomContainer`) takes the same image we already publish to ACR.

This is a strictly better fit than ACI for our use case (per-user, short-lived, untrusted-code execution), and it eliminates the shared-CA fallback path entirely.

## Goals / Non-Goals

**Goals:**
- One sandbox runtime: dynamic sessions. Delete the ACI service, the shared Container App sandbox, and the `USE_ACI_SANDBOX` toggle.
- Per-task isolation with subsecond allocation (vs ~30–120s ACI cold-start).
- Use the existing sandbox image (`sandbox/Dockerfile`) and skill-mount entrypoint unchanged. Skills sync at session warmup, identical to ACI behavior.
- Use Entra ID + the backend's existing managed identity to authenticate to the pool management endpoint (no shared secrets).
- Hide the runtime change from upstream code paths: `_sandbox_exec`, file downloads, and the live-preview proxy continue to call `{base_url}/path` — only the URL builder changes.
- Local dev unchanged: `docker compose` still runs the sandbox container; backend detects "no session pool configured" and falls back to a local `http://sandbox:3000` URL.

**Non-Goals:**
- We do **not** adopt the platform's built-in code-interpreter pool type — we need our customized image (Copilot CLI, gh CLI, skills mount).
- No multi-region session pools in this change. Single pool in the env's region.
- No autoscale tuning beyond default `readySessionInstances`. Capacity sizing is a follow-up.
- No change to the dev-task pipeline orchestration model. Stages, SSE streaming, and Cosmos state are unchanged.
- No live in-flight migration of tasks running on ACI at deploy time — they're short-lived and the cutover is one deploy.

## Decisions

### 1. Use a custom-container session pool, not the built-in code interpreter

**Why:** We need our own image (Copilot CLI, `gh`, skills sync entrypoint, sandbox HTTP server on port 3000). The built-in code interpreter pool can't host arbitrary containers and only exposes a fixed code-execution API.

**Alternatives considered:**
- Built-in code interpreter pool — rejected; doesn't fit our HTTP API or our Copilot CLI workflow.
- Stay on ACI — rejected; cold-start, infra surface, and recurring operational issues are the reason for this change.
- Single shared Container App only — rejected; no per-task isolation, regresses the security model that ACI established.

### 2. Use the dev-task ID as the session `identifier`

**Why:** The session pool routes by an opaque `identifier` query param. Reusing our existing task UUID gives one-to-one task↔session mapping, makes session reuse trivial within a single task's lifetime, and means the cooldown naturally maps to "this task is done."

**Trade-off:** A task that runs longer than the pool's session TTL would need either a TTL bump or explicit `stopSession` + reallocate. For our use (dev-task pipelines that run minutes, not hours), default TTL (configurable, typically 30+ minutes) is comfortably sufficient.

### 3. Authenticate to the pool management endpoint with the backend's managed identity

**Why:** No new secret material. Same pattern we use for Cosmos, Blob, ACR. Requires assigning the backend's system-assigned identity the `Azure ContainerApps Session Executor` role on the session pool resource.

**Implementation:** Use `DefaultAzureCredential().get_token("https://dynamicsessions.io/.default")` and attach as `Authorization: Bearer …` on every request to `{poolManagementEndpoint}`.

### 4. Path-forwarding HTTP client wrapper

The session pool URL format is:
```
{poolManagementEndpoint}/code/...     ← built-in interpreter (not used)
{poolManagementEndpoint}/...          ← forwarded to session container
```
With `?identifier={taskId}&api-version=2025-02-02-preview` appended. Path after the management base is forwarded to the session container verbatim (port `targetPort` from pool config).

**Decision:** Build a thin `SessionSandboxClient` that wraps `httpx.AsyncClient`, prepends the management endpoint, injects the bearer token and identifier, and exposes the same `get/post/stream` surface the existing callers use. Callers pass logical paths (`/tasks`, `/tasks/{id}/stream`, `/files/...`) unchanged.

### 5. Skip the `start_provisioning` / `wait_until_ready` split API

ACI required this split to overlap ARM deploy with other work. Sessions allocate in milliseconds from a prewarmed pool — the first HTTP request *is* the allocation. We make a single GET to a `/health` path on session allocation; if it returns 200, we proceed. No background polling, no orphan cleanup, no in-memory IP cache.

`SandboxService` (Cosmos-backed state) records only `sessionIdentifier`, `lastActivity`, and `status`. No more `containerAppUrl` field.

### 6. Container probes for session health

Define a `Liveness` probe (`GET /health`, 10s period) and a `Startup` probe (`GET /ready`, 5s period, 30 attempts) in the pool's `customContainerTemplate`. Our sandbox already exposes `/health`; we add `/ready` to return 200 once skills sync completes. The pool removes unhealthy instances and keeps `readySessionInstances` warm.

### 7. Local development: feature-detect, don't toggle

The old `USE_ACI_SANDBOX` flag is gone. Backend reads `SESSION_POOL_MANAGEMENT_ENDPOINT`:
- **Set** → use `SessionSandboxService`.
- **Unset** → fall back to direct `http://sandbox:3000` (docker-compose default). No environment variable for the user to flip.

### 8. RBAC: `Azure ContainerApps Session Executor` role assignment

Defined in a new `infra/modules/session-pool.bicep` (or extended `rbac.bicep`) scoped to the pool resource, with `principalId` = backend container app's system-assigned identity.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Regional availability** — dynamic sessions GA list is broad but not universal. | Verified target regions (eastus2, westeurope, northeurope, swedencentral) are in the supported list. Add a deploy-time check in `select-model-regions.sh` if we ever add a new region. |
| **Session TTL shorter than task duration** for very long dev-tasks. | Default TTL (30 min) covers current pipelines. Configurable via `lifecycleConfiguration.cooldownPeriodInSeconds`. If a task approaches TTL, our existing per-task SSE keep-alive maintains `lastAccessedAt`, deferring cooldown. |
| **Pool cold-start cost** — keeping `readySessionInstances > 0` has a baseline cost. | Start with `readySessionInstances: 1` (one warm session always). Scale up if observed allocation latency exceeds 200ms. Net cost is still lower than the always-on shared CA + ACI ARM deploys we have today. |
| **Image pull on pool refresh** — when the image updates, the pool refreshes prewarmed instances. | Same image, same registry, same managed identity. Pool refresh is async; ongoing sessions are unaffected. New sessions after a refresh take a one-time hit during repool. |
| **API version churn** — sessions API is still on `2025-02-02-preview` for advanced features (probes, getSession, listSessions). | Pin the API version in code and Bicep. Audit on Azure SDK updates. The `allocate` and stream paths use stable behavior. |
| **Backend lacks RBAC on pool at first deploy** — Bicep dependency ordering. | RBAC module depends on both the pool resource and the backend container app identity. Already a solved pattern in `rbac.bicep` — extend the same. |
| **Local-dev parity** — devs running docker-compose don't exercise the session code path. | The `SessionSandboxClient` is wrapped behind the same interface as `_sandbox_exec`. Add integration tests in CI that hit a real ephemeral pool against the published image. |
| **In-flight ACI groups at cutover** — orphans after deploy. | One-time cleanup script (`scripts/cleanup-aci-orphans.sh`) lists and deletes any remaining `sandbox-*` ACI groups. Run once, then delete the script. |

## Migration Plan

**Deployment is a single `azd up` cycle. No data migration; sandbox state in Cosmos resets per task.**

1. **Pre-deploy** (this PR):
   - Merge the change. CI builds the sandbox image (unchanged Dockerfile + entrypoint, plus a new `/ready` route in the sandbox HTTP server).
2. **Bicep provision**:
   - New: `Microsoft.App/sessionPools` (`session-pool.bicep`) inside the existing managed env, pulling from existing ACR, using existing managed identity for ACR pull.
   - New: role assignment `Azure ContainerApps Session Executor` for backend → pool.
   - Removed: `container-app-sandbox.bicep`, `aci-network.bicep`, `aci-identity.bicep`, `aci-backend-role.bicep`, `enableAciSandbox` param.
   - Backend container app env vars updated: drop `USE_ACI_SANDBOX`, `SANDBOX_URL`, all `ACI_*`; add `SESSION_POOL_MANAGEMENT_ENDPOINT` and `SESSION_POOL_NAME`.
3. **Backend deploy**:
   - New service `session_sandbox_service.py` becomes the sole sandbox client.
   - `aci_sandbox_service.py` deleted along with the orphan-cleanup background task in `main.py`.
   - `sandbox_service.py` (Cosmos state) drops `containerAppUrl`, adds `sessionIdentifier` (the dev-task ID).
4. **Post-deploy verification**:
   - Trigger a dev-task. Confirm session allocates in < 1s (vs ~30s+ on ACI).
   - Confirm `GET /skills` inside the session returns the user's installed skills (entrypoint pulled from Blob).
   - Confirm session is destroyed after cooldown via `listSessions` poll.
5. **Cleanup**:
   - Run `scripts/cleanup-aci-orphans.sh` once to delete any leftover ACI groups from before deploy.
   - Delete the script after.

**Rollback:** This change deletes the ACI/CA-sandbox code paths. Rollback = revert the PR + redeploy. Acceptable because the dev-task pipeline is the only consumer and we have zero persistent state to migrate.

## Open Questions

1. **Pool capacity defaults** — start with `maxConcurrentSessions: 100`, `readySessionInstances: 1`? Tune after observing real usage.
2. **Network isolation** — sessions support optional VNet integration. Do we need it? Our sandbox doesn't access private resources (Cosmos and ACR are the only outbound dependencies, both reachable via public endpoints / managed identity). Decision: **no VNet integration initially**; revisit if we add private-only dependencies.
3. **Per-session resource limits** — pool config sets CPU/memory per session. Default `2 vCPU / 4 GiB` matches current ACI sizing. Confirm during implementation.
4. **Cooldown period** — default vs explicit? Set `cooldownPeriodInSeconds: 600` (10 min) to match typical task durations + buffer.
