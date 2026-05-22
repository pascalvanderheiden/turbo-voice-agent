# Current Focus

**Change in progress:** `sandbox-dynamic-sessions` (openspec)

Replacing the dual ACI + shared Container App sandbox runtime with **Azure Container Apps dynamic session pools** (custom-container type). This also kills the broken `ca-sandbox-*` Container App that caused the recurring `Operation expired` provisioning failures.

**Phase status (48 tasks):**
- Phase 1 (Bicep infra, 1.1–1.8) — IN PROGRESS (Verbal)
- Phase 2 (SessionSandboxClient, 2.1–2.6) — IN PROGRESS (Fenster)
- Phases 3–9 — queued

**Anti-goal:** Do NOT re-introduce the manual AcrPull/RBAC fixes. New `session-pool-role.bicep` owns RBAC for the pool deterministically.
