## 1. Infrastructure: session pool

- [x] 1.1 Create `infra/modules/session-pool.bicep` defining `Microsoft.App/sessionPools` with `containerType: CustomContainer`, ACR image reference, managed identity, container probes, and parameters for capacity/cooldown/cpu/memory
- [x] 1.2 Add Bicep parameters `sessionPoolMaxConcurrent`, `sessionPoolReadyInstances`, `sessionPoolCooldownSeconds`, `sessionPoolCpu`, `sessionPoolMemory` with documented defaults
- [x] 1.3 Wire the module into `main.bicep`, passing the existing `cae-*` environment ID and ACR-published sandbox image
- [x] 1.4 Create `infra/modules/session-pool-role.bicep` assigning `Azure ContainerApps Session Executor` on the pool to the backend container app's managed identity
- [x] 1.5 Add Bicep outputs `sessionPoolManagementEndpoint` and `sessionPoolName`; surface as `SESSION_POOL_MANAGEMENT_ENDPOINT` and `SESSION_POOL_NAME` env vars on the backend container app
- [x] 1.6 Remove `infra/modules/container-app-sandbox.bicep`, `aci-network.bicep`, `aci-identity.bicep`, `aci-backend-role.bicep` and all references in `main.bicep`
- [x] 1.7 Remove ACI parameters (`aciSandboxCpu`, `aciSandboxMemory`, subnet ID, identity ID) from `main.bicep`, `main.parameters.json`, and any `collect-deployment-params.sh`
- [x] 1.8 Verify Bicep builds cleanly: `az bicep build --file infra/main.bicep`

## 2. Backend: SessionSandboxClient

- [x] 2.1 Create `backend/app/services/session_sandbox_client.py` implementing `SessionSandboxClient` (httpx wrapper with token caching from `DefaultAzureCredential` for `https://dynamicsessions.io/.default`)
- [x] 2.2 Implement `request(method, path, *, identifier, ...)` that prepends `SESSION_POOL_MANAGEMENT_ENDPOINT`, attaches Bearer token, injects `identifier` + `api-version=2025-02-02-preview` query params
- [x] 2.3 Implement `stream(path, *, identifier, ...)` for SSE (`Accept: text/event-stream`) yielding events as they arrive
- [x] 2.4 Implement `stop_session(identifier)` calling `POST /.management/stopSession?identifier=...`, tolerating 404
- [x] 2.5 Implement single-retry on 401/403 with token refresh
- [x] 2.6 Write unit tests using `respx` covering: URL composition, identifier propagation, token attachment, retry on 401, SSE streaming, stop_session

## 3. Backend: wire client into sandbox callers

- [x] 3.1 Update `backend/app/services/sandbox_service.py`: drop `containerAppUrl`, add `sessionIdentifier` to `SandboxState`; remove per-task IP cache
- [x] 3.2 Replace all `_sandbox_exec` and shared `SANDBOX_URL` HTTP usage with `SessionSandboxClient.request(...)` keyed by dev-task UUID
- [x] 3.3 Replace SSE streaming code with `SessionSandboxClient.stream(...)`
- [x] 3.4 Replace file/skill endpoint calls with the client (paths unchanged)
- [x] 3.5 On user-initiated cancellation or task deletion, call `client.stop_session(task_id)`
- [x] 3.6 Local-dev fallback: when `SESSION_POOL_MANAGEMENT_ENDPOINT` is unset, route to `http://sandbox:3000` (existing docker-compose behavior)
- [x] 3.7 Add Cosmos schema migration / lazy upgrade so old `containerAppUrl` documents are ignored

## 4. Backend: remove ACI implementation

- [ ] 4.1 Delete `backend/app/services/aci_sandbox_service.py`
- [ ] 4.2 Delete the orphan-ACI cleanup background task in `backend/app/main.py` and its registration
- [ ] 4.3 Remove `USE_ACI_SANDBOX` from backend settings/env, code branches, docs
- [ ] 4.4 Remove split-provisioning API (`start_provisioning`/`wait_until_ready`) since allocation is now implicit on first request
- [ ] 4.5 Remove ACI-related tests; update or rewrite affected sandbox tests to target `SessionSandboxClient`

## 5. Sandbox image: warm-up readiness

- [x] 5.1 Update `sandbox/entrypoint.sh` (or equivalent) so skills sync from Blob Storage completes before the HTTP server reports `/ready`
- [x] 5.2 Add or confirm `GET /ready` returns 200 only after skills sync and server are up; `GET /health` remains a lightweight liveness check
- [x] 5.3 Add a request middleware that reads `X-GH-Token` on first request and runs `gh auth login --with-token`, then clears the in-process token
- [x] 5.4 Smoke-test the image locally with docker run, verifying probes and `X-GH-Token` handling

## 6. Auth & token flow

- [ ] 6.1 Update backend code that previously injected `GH_TOKEN` into ACI env to instead attach `X-GH-Token` header on the first session call for the task
- [ ] 6.2 On "Disconnect" in profile settings, call `SessionSandboxClient.stop_session(...)` for any active sessions belonging to that user
- [ ] 6.3 Update `sandbox-auth` related backend tests for the header-based token flow

## 7. Deployment & migration

- [x] 7.1 Add `scripts/cleanup-aci-orphans.sh` (one-shot, idempotent) that deletes leftover `sandbox-*` ACI container groups in the resource group
- [x] 7.2 Document a single `azd up` cycle in `README.md` / `docs/` covering: pool provisioning, role assignment, ACI/Container App cleanup
- [ ] 7.3 Run `azd up` in a dev subscription; verify pool exists, backend env has `SESSION_POOL_MANAGEMENT_ENDPOINT`, role assignment present _(awaits Phase 4 + 6 — validation wave)_
- [ ] 7.4 Run end-to-end smoke test: trigger a dev-task → confirm session allocation (<2s), `/tasks` accepted, SSE streamed, task completes, session destroyed after cooldown _(awaits Phase 4 + 6 — validation wave)_

**Phase 7 prep also done (out-of-band, not in original task list):**
- [x] Fix `azure.yaml` sandbox service: removed broken `host: containerapp` entry (no Container App exists). Sandbox image now built directly to ACR as `turbo-voice-agent/sandbox:latest` via `infra/scripts/build-sandbox-image.sh` (azd `postprovision` + `postdeploy` hook). Replaces the older `tag-sandbox-latest.sh` push-then-retag dance. Image tag matches `infra/main.bicep:263`.
- [x] `az bicep build --file infra/main.bicep` clean after changes.

## 8. Observability & docs

- [ ] 8.1 Add structured logging in `SessionSandboxClient` for: allocation latency, request latency, identifier, status code, retry count
- [ ] 8.2 Emit App Insights custom event `sandbox.session.allocated` / `sandbox.session.stopped` for dashboarding
- [ ] 8.3 Update `AGENTS.md` and `README.md` to describe the new architecture and remove ACI references
- [ ] 8.4 Add a short troubleshooting section: 401 from pool (RBAC propagation), 429 (concurrency cap), probe failures
- [ ] 8.5 Update `docs/architecture.md` (or equivalent) diagram to show session pool instead of ACI/Container App sandbox

## 9. Final verification

- [ ] 9.1 Run backend test suite: `cd backend && pytest`
- [ ] 9.2 Run lint: `cd backend && ruff check . && ruff format --check .`
- [ ] 9.3 Frontend smoke (no functional UI change expected, but verify dev-task flow): `cd frontend && npm run lint && npx playwright test e2e/dev-task.spec.ts` (or equivalent)
- [ ] 9.4 Confirm `azd up` succeeds on a clean subscription with no manual steps
- [ ] 9.5 Confirm cold-start latency for a sandbox task is under 2 seconds (vs prior ~30-120s ACI)
- [ ] 9.6 Run `openspec status --change sandbox-dynamic-sessions` and confirm apply-ready
