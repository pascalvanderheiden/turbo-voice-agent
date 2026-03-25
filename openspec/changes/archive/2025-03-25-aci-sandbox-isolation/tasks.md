## 1. Infrastructure (Bicep)

- [x] 1.1 Create `infra/modules/aci-sandbox.bicep` — ACI container group resource definition with params for image, CPU, memory, subnet ID, managed identity ID, env vars (PORT, BACKEND_URL, COPILOT_MODEL, AZURE_STORAGE_ACCOUNT_NAME, GH_TOKEN)
- [x] 1.2 Create `infra/modules/aci-identity.bicep` — user-assigned managed identity resource with AcrPull role on container registry and Storage Blob Data Reader on skills storage account
- [x] 1.3 Add VNet subnet `snet-aci-sandbox` with `/24` CIDR and `Microsoft.ContainerInstance/containerGroups` delegation to `infra/modules/container-apps-env.bicep` (or a new VNet module)
- [x] 1.4 Add NSG for ACI subnet — allow inbound TCP 3000 from Container Apps subnet, deny all other inbound
- [x] 1.5 Wire new modules into `infra/main.bicep` — pass subnet ID, identity ID, ACR login server, storage account name as outputs/params. Add `USE_ACI_SANDBOX=true` env var to backend Container App
- [x] 1.6 Update `azure.yaml` — remove sandbox as always-on service (or keep for fallback); add ACI image as build target if needed

## 2. Backend — ACI Sandbox Service

- [x] 2.1 Create `backend/app/services/aci_sandbox_service.py` — service class using `azure-mgmt-containerinstance` SDK with methods: `create_container_group(task_id, env_vars)`, `get_container_ip(task_id)`, `delete_container_group(task_id)`, `is_ready(task_id)`
- [x] 2.2 Add `azure-mgmt-containerinstance` and `azure-identity` to `backend/pyproject.toml` dependencies
- [x] 2.3 Add configuration constants — resource group name, subnet ID, identity resource ID, ACR image reference, default CPU/memory. Source from env vars set by Bicep.
- [x] 2.4 Implement health polling in `create_container_group` — after ARM create, poll provisioning state + `GET /health` on private IP until ready (timeout 120s)
- [x] 2.5 Add orphan cleanup background task — `asyncio.create_task` in `main.py` lifespan that runs every 15 minutes, lists `sandbox-*` container groups, deletes any >2 hours old without an active dev-task

## 3. Backend — Pipeline Integration

- [x] 3.1 Add `USE_ACI_SANDBOX` feature flag in `dev_agent.py` — read from env, default `False`
- [x] 3.2 Refactor `_sandbox_exec` to resolve sandbox URL per-task — if ACI mode, look up container IP from `aci_sandbox_service`; otherwise use static `SANDBOX_URL`
- [x] 3.3 Add ACI provisioning to pipeline start — in `_run_mockup_pipeline`, `_run_sequential_pipeline`, `_run_slides_pipeline`, call `aci_sandbox_service.create_container_group()` before the init stage. Stream "Provisioning sandbox..." to terminal output.
- [x] 3.4 Add ACI teardown to pipeline end — after `svc.set_status(task_id, "completed"/"failed")`, call `aci_sandbox_service.delete_container_group(task_id)`
- [x] 3.5 Update `cancel_sandbox_task_for()` — also delete ACI container group when a task is cancelled/deleted
- [x] 3.6 Inject GitHub token at ACI creation — pass user's stored GH token as secure env var `GH_TOKEN` in container group definition
- [x] 3.7 Update `routes/dev.py` live preview proxy — resolve sandbox URL per-task for preview start/stop/proxy endpoints

## 4. Sandbox Image Changes

- [x] 4.1 Update `sandbox/entrypoint.sh` — if `GH_TOKEN` env var is set, run `echo "$GH_TOKEN" | gh auth login --with-token` before starting the server
- [x] 4.2 Add `SINGLE_TASK_MODE` env var support — when set, sandbox server exits (process exit 0) after the last task completes instead of staying idle
- [x] 4.3 Verify `sync-skills.sh` works with user-assigned managed identity — test `az login --identity --client-id $UAI_CLIENT_ID` flow

## 5. Testing

- [x] 5.1 Add unit tests for `aci_sandbox_service.py` — mock Azure SDK, test create/poll/delete/cleanup flows
- [x] 5.2 Add integration test for feature flag toggle — verify ACI mode vs Container App fallback routing
- [x] 5.3 Update Playwright e2e tests — verify dev-task creation and stage progression works with ACI (or mock)
- [x] 5.4 Manual smoke test — run a full mockup pipeline with ACI enabled in staging, verify sandbox provisioning → pipeline → teardown

## 6. Cutover & Cleanup

- [x] 6.1 Deploy infra with `azd provision` — VNet subnet, managed identity, RBAC, backend env var
- [x] 6.2 Enable `USE_ACI_SANDBOX=true` in production backend env
- [x] 6.3 Monitor for 1 week — check orphan cleanup, cold-start latency, cost
- [x] 6.4 Scale Container App sandbox to 0 replicas (keep deployed for rollback)
- [x] 6.5 Remove `container-app-sandbox.bicep` after successful validation period
