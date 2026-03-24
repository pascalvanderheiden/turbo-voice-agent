## Context

The sandbox runs as a single Azure Container App (`ca-sandbox-{env}`, 2 CPU / 4GB, `maxReplicas: 1`). All dev-tasks share one Node.js process with directory-level isolation (`/workspace/{task_id}`). The backend talks to it via internal FQDN over HTTP/1.1 for SSE streaming.

Problems: no kernel isolation between tasks, resource contention, single point of failure, no horizontal scaling. The sandbox image is already self-contained (Node.js server + Copilot CLI + Playwright) and published to ACR.

Key constraint: the backend must continue using the same HTTP protocol (POST /tasks, GET /tasks/{id}/stream, DELETE /tasks/{id}) — only the target URL changes from a static env var to a per-task resolved endpoint.

## Goals / Non-Goals

**Goals:**
- Each dev-task gets a dedicated ACI container group with its own CPU/memory/filesystem
- Backend dynamically provisions ACI on task creation, tears down on completion/failure
- Maintain existing SSE streaming protocol between backend and sandbox
- Private networking — ACI containers not exposed to the internet
- Pay-per-use billing (no always-on sandbox cost when idle)
- Skills loaded from blob storage at container startup

**Non-Goals:**
- GPU workloads or custom VM sizes (standard ACI SKUs are sufficient)
- Persistent storage across tasks (each task starts fresh)
- Mid-task hot-reload of skills (skills baked in at container start)
- Migrating the sandbox server.js to a different runtime
- WebSocket support (SSE over HTTP/1.1 is sufficient)

## Decisions

### D1: ACI container group per dev-task (not per-stage)

One ACI container group is provisioned when a dev-task is created and lives for the entire pipeline (init → skills → implement → screenshots). This avoids cold-start latency between stages and allows `--continue` sessions to share state.

**Alternative**: ACI per-stage — rejected because cold-start per stage (30-60s × 4 stages) adds 2-4 minutes overhead, and Copilot CLI `--continue` requires the same process.

### D2: VNet-integrated ACI with Container Apps Environment subnet

ACI container groups deploy into a delegated subnet within the same VNet as the Container Apps Environment. The backend reaches ACI containers via private IP. No public IP assigned.

**Alternative**: Public IP with auth token — rejected because it exposes the sandbox to the internet and requires token rotation.

### D3: Managed Identity for ACR pull and Blob access

Each ACI container group uses a **user-assigned managed identity** (shared across all ACI instances) with AcrPull on the container registry and Storage Blob Data Reader on the skills blob container. This avoids per-container identity creation overhead.

**Alternative**: System-assigned identity per ACI — rejected because creating a new identity per task adds latency and cleanup complexity.

### D4: Backend ACI client using Azure SDK (`azure-mgmt-containerinstance`)

The backend uses the Azure Python SDK to create/poll/delete container groups. Container group names follow the pattern `sandbox-{task_id_short}` (first 8 chars of UUID to stay within ACI naming limits).

**Alternative**: ARM REST API directly — rejected because the SDK handles retries, auth, and pagination.

### D5: Early provisioning — start ACI on task creation

ACI provisioning starts immediately when the backend creates a dev-task (before the pipeline runs). The pipeline init stage polls for ACI readiness. This overlaps the ~30-60s cold-start with task setup time.

### D6: Sandbox image unchanged, single-task entrypoint mode

The same Docker image is used. A new env var `SINGLE_TASK_MODE=true` tells the sandbox to skip the Express server idle loop and exit when the last task completes. The server still exposes the same HTTP API.

### D7: Graceful teardown with timeout

On pipeline completion (or failure), the backend deletes the ACI container group. If deletion fails, a background cleanup job sweeps orphaned container groups older than 2 hours.

## Risks / Trade-offs

- **[Cold-start latency]** ACI takes 30-60s to provision → Mitigated by early provisioning (D5). User sees "Provisioning sandbox..." in the init stage.
- **[Cost at high volume]** If many tasks run concurrently, ACI cost may exceed the fixed Container App cost → Monitor with Azure Cost Management; add budget alerts.
- **[Orphaned containers]** If backend crashes mid-pipeline, ACI container groups are left running → Background cleanup job (D7) sweeps orphans every 15 minutes.
- **[ACI limits]** Default ACI quota is ~100 container groups per subscription per region → Sufficient for current scale; request quota increase if needed.
- **[Skills freshness]** Skills loaded at container start, not hot-reloaded → Acceptable trade-off; next task picks up new skills automatically.
- **[Networking complexity]** VNet subnet delegation adds infra complexity → One-time setup; well-documented Azure pattern.

## Migration Plan

1. **Phase 1 — Infrastructure**: Add Bicep modules for VNet subnet, user-assigned managed identity, RBAC roles. Deploy alongside existing sandbox Container App.
2. **Phase 2 — Backend**: Add `AciSandboxService` with create/poll/delete. Feature-flag `USE_ACI_SANDBOX=true` to switch between old (Container App) and new (ACI) sandbox.
3. **Phase 3 — Cutover**: Enable feature flag in production. Monitor for 1 week. Remove old Container App sandbox.
4. **Rollback**: Disable feature flag → falls back to shared Container App sandbox (still deployed in Phase 1-2).

## Open Questions

- Should ACI containers have a time-to-live cap (e.g., max 2 hours) to prevent runaway tasks?
- Should the cleanup job run in the backend (background asyncio task) or as a separate Azure Function on a timer?
