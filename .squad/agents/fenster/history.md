# Fenster — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI backend, Cosmos DB, Azure Voice Live API.
User: the project maintainer.

Backend has 12 specialist agents: notes, brainstorm, research, spec, dev, marketing, slides, skills, todo, work + supervisor. Service layer pattern with dual Cosmos DB + InMemory implementations.

## Core Context

**Architecture Patterns (pre-2026-05):**
- Slides pipeline: `init → slides → run` stages (skills sync in init, Slidev server in run).
- Sandbox abstraction: SandboxClient protocol with SessionSandboxClient (dynamic sessions) and LocalSandboxClient (docker-compose) backends.
- Split provisioning: start sandbox → gather content in parallel → wait for health (cold-start optimization).
- Connection error discipline: unreachable local services log at debug/warning level, never exception() with tracebacks.
- Skills service: dual Cosmos/InMemory implementations; in-memory writes to `.agents/skills/` disk when blob storage unavailable.
- Live preview: restart-on-demand with health check; workspace existence validated via sandbox `/files/` before start.
- OSS scrubbing: `.env.example` placeholders only (`<your-...>`), generic metadata in pyproject.toml, neutral example domains.

**Key Files:**
- `backend/app/agents/dev_agent.py` — pipeline orchestration (init/slides/run)
- `backend/app/services/session_sandbox_client.py` — dynamic sessions HTTP client (19 unit tests)
- `backend/app/services/docker_sandbox_service.py` — local sandbox lifecycle
- `backend/app/services/in_memory_skills_service.py` — disk-backed skills fallback
- `.github/copilot-instructions.md` — refreshed 2026-05-22 for OSS + dynamic sessions

For detailed pre-2026-05 learnings, see git history (commits c8db9e4–2a7e013).

## Team Updates

- **2026-05-22:** Verbal diagnosed and recovered failed `azd up` deployment. Root cause: Bicep RBAC module dependency ordering catch-22 — backend Container App identity had zero role assignments because RBAC module depends on backend being healthy, creating circular dependency. Manual fix: `az role assignment create` granted AcrPull to backend identity. **Action required:** Run `azd provision` then `azd deploy` to complete deployment. Permanent fix: Two-phase RBAC Bicep refactor proposed (see `.squad/decisions/decisions.md`).
- **2026-05-20:** Verbal deployed quota-aware region selector (`infra/scripts/select-model-regions.sh`) as `azd` preprovision hook. Three new env vars in CI/CD pipelines: `AZURE_OPENAI_LOCATION_PRIMARY`, `AZURE_OPENAI_LOCATION_VOICE`, `AZURE_OPENAI_LOCATION_RESEARCH`. This resolves fresh `azd up` quota failures on new subscriptions and enables interactive region selection for multi-region deployments.

- **2026-05-27:** Redfoot archived `sandbox-dynamic-sessions` OpenSpec change (49/50 tasks complete, production verified subsecond session allocation); 7 spec deltas merged into canonical library. See `.squad/decisions/decisions.md`.

## Learnings
- Cache-cold-on-deploy failure mode: in-memory caches that mirror persistent storage MUST fall back to the source on miss, especially when the cache is process-local and lost on redeploy. Check every future cache helper for cache miss → source read → cache warm behavior before relying on it in background agents or pipelines.
- Slides pipeline restructured from `init→skills→slides` to `init→slides→run`. Skills sync merged into init stage (it's infrastructure, not user-visible). Slides stage now uses `copilot --autopilot --yolo` via shell command instead of `_sandbox_exec(prompt=...)`. Run stage handles npm install + dev server + health check, auto-registering the preview URL in `_live_previews`.
- The `_sandbox_exec()` helper supports both `prompt` (Copilot CLI) and `command` (shell) modes. For the new slides stage, piping the prompt into `copilot --autopilot --yolo` via command mode avoids the model parameter dependency.
- The `start_live` route no longer starts a server — it's just a URL lookup now. The run stage in the pipeline owns the server lifecycle.
- Default deck config changed from `theme=shadcn/ui, palette=arctic` to `theme=default, palette=blue` per spec.
- ACI sandbox cold-start optimization: `aci_sandbox_service.py` now supports split provisioning (`start_provisioning()` + `wait_until_ready()`) so callers can overlap content gathering with the ARM deploy. Health poll interval reduced from 5s→2s, and once ARM succeeds a fast poll (0.5s) kicks in for the health check. Progress callbacks emit granular `[sandbox]` status messages to the pipeline terminal buffer.
- The slides pipeline in `dev_agent.py` uses split provisioning: starts ACI, gathers slides content from Cosmos in parallel, then waits for health. Mockup and sequential pipelines still use the all-in-one `_provision_aci_sandbox()` since they have no overlapping work before the first sandbox exec.
- The real cold-start bottleneck is the ARM API + ACR image pull (~30-60s). Reducing that further requires infra changes: pre-warmed container pools, Always Ready replicas, or switching to Container Apps Jobs. The polling optimizations shave ~3-10s off the tail.
- Local dev graceful degradation: ACI sandbox init in `main.py` is now wrapped in try/except so `USE_ACI_SANDBOX=true` without Azure creds won't crash startup. Pipeline entry in `dev_agent.py` now pre-flight checks sandbox reachability (skipped for ACI mode which provisions on-demand) and fails fast with an actionable message instead of raw httpx connection errors. Blob storage operations in `cosmos_skills_service.py` use `logger.warning()` with concise messages instead of `logger.exception()` which dumped full REST tracebacks. Sandbox skill sync functions in `main.py` suppress connection-refused noise to `logger.debug()` level for local dev.
- Pattern: Connection errors from unreachable local services (sandbox, blob storage) should be logged at debug/warning level with clean messages, never `logger.exception()` with full tracebacks. Reserve `exception()` for unexpected failures in production-critical paths.
- PPTX upload fix: `upload.py` `ALLOWED_TYPES` now includes PPTX MIME type (`application/vnd.openxmlformats-officedocument.presentationml.presentation`). Without this, the Slides page's PowerPoint template upload returned 400 "Unsupported type" — the file never reached the server.
- ~~PDF export local fallback~~ **REMOVED**: All backend PDF export/download code for slides was removed. Deckio handles PDF export natively from its webapp, making backend PDF generation redundant. Removed: `_upload_slides_pdf`, `_upload_pdf_to_blob`, `_save_pdf_locally` methods from `dev_agent.py`; `download_pdf` route from `dev.py`; `pdf_url` field from `DevExportArtifacts` model. The `set_export_artifacts` service method and `DevExportArtifacts` model remain for `code_url`. Non-slides PDF utilities (extraction.py for brainstorm) are untouched.
- Skills service now has an in-memory fallback implementation matching the pattern used by all other services (notes, ideas, dev tasks, etc.). When Cosmos DB is unavailable, `main.py` now instantiates `InMemorySkillsService` instead of leaving `_cosmos_skills` as None, eliminating the "Skills service not available" error. The in-memory service supports all core operations: `activate_skill`, `deactivate_skill`, `list_activated`, `get_skill`, `get_npx_commands`, and `with_user` for multi-tenant isolation. Blob upload methods are no-ops (log warning and return empty list) since blob storage requires Azure credentials. Data stored in nested dict: `{user_id: {skill_name: skill_data}}`.
- Local Docker sandbox auto-start: Created `docker_sandbox_service.py` that automatically starts the sandbox container via `docker compose up -d sandbox` during backend startup when ACI is not configured. The service checks if Docker is available, starts the container, polls for health at `SANDBOX_URL` (default `http://localhost:4000`), and stops the container on backend shutdown. Gated by `AUTO_START_SANDBOX` env var (default `true`). Only activates when `USE_ACI_SANDBOX` is not `true`. If the sandbox is already running, it skips startup and doesn't stop it on shutdown. The docker-compose.yml already had a `sandbox` service defined — this just auto-manages its lifecycle. Files: `backend/app/services/docker_sandbox_service.py` (new), `backend/app/main.py` (lifespan wiring).
- Local skill installation to disk: `InMemorySkillsService` now accepts `local_skills_dir: Path` and writes skill files to `.agents/skills/{skill-name}/` on activate (marketplace skills via GitHub download) and deletes them on deactivate. The `upload_local_skills` endpoint in `dev.py` falls back to writing to `LOCAL_SKILLS_DIR` when blob storage is unavailable. `main.py` resolves `LOCAL_SKILLS_DIR` from env var or `{project_root}/.agents/skills/`. The docker-compose volume mount (`.agents/skills:/home/agent/.copilot/skills:ro`) means the sandbox sees changes immediately — no restart needed. Azure path unchanged: blob storage + sandbox sync. `.agents/skills/` added to `.gitignore`. Files: `backend/app/services/in_memory_skills_service.py`, `backend/app/main.py`, `backend/app/routes/dev.py`, `.gitignore`.
- Live preview restart for completed tasks: Added `_restart_dev_server()` helper in `dev.py` that restarts the sandbox dev server from persisted workspace files. The `start_live_preview` endpoint (POST `/api/dev/{task_id}/live`) now probes whether the registered server is actually reachable, clears stale entries, and calls `_restart_dev_server` to relaunch. Detects mode (slides→port 3333, mockup/sequential→port 3000) and uses the matching command strategy (npm run dev with fallback to npx serve). Checks workspace existence via sandbox `/files/` endpoint before attempting start; returns HTTP 410 if workspace is gone. The `proxy_live_preview` auto-recovery also calls `_restart_dev_server` instead of just registering a URL entry. Pattern: always verify server health before trusting `_live_previews` entries — they survive in-memory but the sandbox process may not.
- OSS backend scrub: `backend/.env.example` is the highest-risk backend artifact for personal Azure references. Keep every example value resource-agnostic (`<your-...>` placeholders), add a source comment above each variable, and leave `AUTH_DISABLED=true` enabled for local development.
- Backend metadata for OSS should stay generic: `pyproject.toml` now uses a contributors-only author entry, a generic backend description, and explicit `license = { text = "MIT" }` with no repository URL baked in.
- Non-secret custom domains can still leak environment context: replaced the local mock user email (`dev@turboagent.nl`) and preview-domain docstring (`voice.turboagent.nl`) with neutral examples during the OSS scrub.

## Learnings — 2026-05-22 (sandbox-dynamic-sessions Phase 2)

**Work:** Implemented `SessionSandboxClient` (tasks 2.1–2.6) — HTTP client for Azure Container Apps Dynamic Sessions management API. Files: `backend/app/services/session_sandbox_client.py` + `backend/tests/test_session_sandbox_client.py` (19 tests, all green). Added `respx>=0.22.0` dev dep. Commit `bcdb0bf`.

**Patterns to remember:**
- Use `respx` (httpx-native) for mocking outbound HTTP in tests instead of `requests-mock` or hand-rolled stubs.
- The session pool management endpoint contract is `{SESSION_POOL_MANAGEMENT_ENDPOINT}` + `{SESSION_POOL_NAME}` — both injected as env vars by infra (Verbal). Don't hardcode.
- Commits can sweep in unrelated pre-staged work from disk — always `git status` before commit and call out anything unexpected in the message. `bcdb0bf` swept in Phase 1 Bicep changes that had three latent schema bugs; Verbal had to clean up afterwards in `b70212d`.

## 2026-05-22: Phase 3 — SandboxClient abstraction
Refactored ~25 httpx call sites in `dev_agent.py`, `routes/dev.py`, `routes/sandbox.py` to route through unified `SandboxClient` protocol (`SessionSandboxClient` for ACA dynamic sessions, `LocalSandboxClient` for docker-compose). Factory `get_sandbox_client()` lazy-selects via `SESSION_POOL_MANAGEMENT_ENDPOINT` env var. Schema: `containerAppUrl` → `sessionIdentifier` with lazy upgrade (read tolerates legacy field, write never emits it). ACI helpers became no-op shims to preserve call sites; Phase 4 removes them.

**Learnings:**
- Drop a shared `httpx.AsyncClient(...)` context manager when refactoring to a client method — the indentation collapse breaks the body indent by 4 spaces. Always re-check ruff/AST after such edits.
- For admin endpoints with no dev-task identifier (e.g., `/health`, `/tasks` listing in `routes/sandbox.py`), use a synthetic `"admin"` identifier. In local-dev `LocalSandboxClient` ignores it; in session-pool mode it allocates a dedicated admin session.
- `SandboxClient.stream_response` is an `@asynccontextmanager` yielding `httpx.Response` so consumers can call `aiter_lines()` — critical for SSE proxies and `_sandbox_exec` streaming.

- **2026-05-22 (Scribe stamp):** Phase 3 refactor committed as `cfd9318`. Sandbox-dynamic-sessions status: Phases 1, 2, 3, 5 ✅ complete. Phases 4 (delete ACI), 6 (infra wiring), 7 (env/config docs), 8 (validation), 9 (archive) remain.

## 2026-05-22 — sandbox-dynamic-sessions Phase 4 + Phase 6

**Phase 4 — ACI removal (commit 88558ab):**
- Deleted `backend/app/services/aci_sandbox_service.py` (353 lines) and `backend/tests/test_aci_sandbox_service.py`.
- Removed ACI orphan-cleanup background task and `USE_ACI_SANDBOX` branches from `main.py` lifespan; the dynamic-session pool needs no orphan cleanup (pool cooldown handles it).
- Stripped `_provision_aci_sandbox` / `_start_aci_provisioning` / `_finish_aci_provisioning` shims and all their call sites from `dev_agent.py`. Renamed `_teardown_aci_sandbox` → `_teardown_sandbox_session` since it now exclusively calls `client.stop_session`.
- Dropped `ACI_IDENTITY_CLIENT_ID` branch from `sandbox/sync-skills.sh` — the session pool uses system-assigned managed identity exclusively.
- No env vars to remove from `.env.example` (none of `USE_ACI_SANDBOX`, `ACI_*` were ever documented there).

**Phase 6 — X-GH-Token + disconnect (commit fbaa199):**
- Replaced the body-based `payload["ghToken"]` injection in `_sandbox_exec` with header-based `X-GH-Token` on the FIRST sandbox request per dev-task. Track via module-level `_gh_token_sent: set[str]`; cleared by `cancel_sandbox_task_for` and `_teardown_sandbox_session`.
- Extended `DELETE /api/me/connections/github-sandbox`: enumerate the user's dev-tasks in `{running, provisioning, pending}` and call `client.stop_session(task_id)` for each before clearing the PAT. Response now includes `stoppedSessions` count.
- Exposed `dev_service` on `app.state` so the disconnect route can iterate the user's tasks.

**Test posture:** All 43 sandbox-related tests pass (8 new in Phase 6). The pre-existing 18 Entra auth failures are untouched and unrelated.

**Surprises / decisions:**
- The sandbox container still accepts `ghToken` in the POST `/tasks` body (Phase 5 leaves that path for backwards compat), but I removed the body injection from the backend per the spec — header is the sole bootstrap path now.
- `_sandbox_exec` is the natural choke point for first-call header injection because the cleanup stage in every pipeline (`_run_mockup_pipeline`, `_run_sequential_pipeline`, `_run_slides_pipeline`) is the first sandbox HTTP call for the dev-task. No other entry point precedes it.
- Used in-memory `_gh_token_sent` set (not a Cosmos field) per the spec's allowance — sessions are ephemeral, the middleware is idempotent, and process restarts trigger an acceptable re-bootstrap.

**Files touched:**
- backend/app/agents/dev_agent.py — header injection, tracker, renamed teardown helper
- backend/app/main.py — drop ACI lifespan block, expose dev_service
- backend/app/routes/user.py — disconnect_sandbox stops active sessions
- backend/app/services/session_sandbox_client.py — docstring updated for X-GH-Token contract
- backend/tests/test_dev_agent_gh_token.py — NEW (5 tests)
- backend/tests/test_sandbox_disconnect.py — NEW (3 tests)
- sandbox/sync-skills.sh — drop ACI_IDENTITY_CLIENT_ID
- openspec/changes/sandbox-dynamic-sessions/tasks.md — 4.1-4.5, 6.1-6.3 checked

## 2025-11-25 — Phase 8: structured logging + docs refresh

**Scope:** Observability and documentation for the dynamic-sessions sandbox. Tasks 8.1–8.5.

**Changes:**
- `backend/app/services/session_sandbox_client.py`:
  - Renamed module logger to `log` (kept `logger` alias for backwards compat).
  - Added `_allocated: set[str]` to track first-request-per-identifier so we can emit `sandbox.session.allocated` once per session.
  - `request()` now measures latency, emits structured DEBUG `sandbox.session.request` on every call, WARNING `sandbox.session.error` on retry + on any final 4xx/5xx, and INFO `sandbox.session.allocated` on the first <400 response per identifier.
  - `stop_session()` gained `reason: str = "complete"` kwarg, emits INFO `sandbox.session.stopped` with reason field. Identifier dropped from `_allocated` so re-use re-emits.
  - `SandboxClient` Protocol and `LocalSandboxClient.stop_session()` updated to accept the new kwarg.
- `AGENTS.md` — NEW (replaced empty stub). Short agent-facing companion to `.github/copilot-instructions.md` covering architecture, sandbox flow, observability event table, troubleshooting pointer.
- `README.md` — added sandbox bullet + "How sandbox execution works" subsection + extended Mermaid diagram with session pool node. No ACI references remained.
- `infra/README.md` — added Troubleshooting section: 401/403 RBAC propagation, 429 concurrency cap, probe failures (skill-sync marker), cold start >5s.
- `openspec/changes/sandbox-dynamic-sessions/tasks.md` — 8.1–8.5 checked.

**Decisions logged:** `.squad/decisions/inbox/fenster-phase8.md`
- App Insights SDK wiring deferred; using structured-log fallback with `event` prefix `sandbox.`
- "Allocated" event triggered on first successful request (no explicit allocate API)
- `stop_session(reason=...)` kwarg added

**Verification:**
- `pytest tests/test_session_sandbox_client.py` — 19/19 pass
- `pytest -k "sandbox or session"` — 31/31 pass (+5 skipped, unrelated)
- `ruff check .` + `ruff format .` — clean on touched files
- Pre-existing unrelated failure: `tests/test_notes_api.py::test_list_notes` (401 vs 200, auth issue, predates Phase 8)

**Learnings:**
- Backend has no App Insights SDK imports (verified by grep). The structured-log fallback is the cheapest forward-compatible path; a future opencensus handler can filter `record.event.startswith("sandbox.")` and call `track_event`.
- The session pool has no explicit "allocate" call — first request is the allocation. Tracking `_allocated` in the client gives us a one-shot signal per session.
- Identifiers (dev-task UUIDs) are safe to log; tokens/PATs/response bodies are not. The hygiene rule is enforced by only logging fields explicitly listed in the event table.

## 2026-05-22T18:00Z — Sandbox /tasks 400 root cause analysis

**Triggered by:** Pascal's first E2E run on the session pool. Allocation worked, but
implement step hit `400 Bad Request` from the sandbox container (proxied via pool).

**Diagnosis:** Phase-4→Phase-6 regression in the backend↔sandbox auth handshake.

- Pre-Phase-6 backend included `payload["ghToken"] = gh_token` in the body of
  every `/tasks` POST. Sandbox handler at `server.js:178` checks
  `effectiveToken = perTaskToken || ghToken (env)` and 400s if missing.
- Phase 6 (commit `fbaa199`) moved the PAT to `X-GH-Token` header on first call,
  added middleware (`server.js:79–105`) that runs `gh auth login --with-token`
  and flips `ghAuthenticated = true`. Removed body field.
- BUT the `/tasks` handler was not updated to honour `ghAuthenticated`. It still
  fails on missing body/env token even though middleware just authenticated.

In session-pool mode the pool containers have no `GH_TOKEN` env (no per-user
env on shared/ephemeral pool containers), so neither path is satisfied → 400.

**Output:** Wrote full diagnosis + fix options to
`.squad/decisions/inbox/fenster-sandbox-handshake-diagnosis.md`. Recommended
Fix A (5-line change in `sandbox/server.js`): tolerate `ghAuthenticated` as a
valid auth state in the `/tasks` handler. No backend code change needed.

Also noted that the "No skills available in sandbox" message is independent —
`/skills/sync` returns `{synced: 0}` because the pool container image likely
lacks `AZURE_STORAGE_ACCOUNT_NAME` env or RBAC on the storage account, or no
blobs exist. That's Verbal's infra domain. The protocol path is correct.

**Key files inspected:**
- `backend/app/agents/dev_agent.py::_sandbox_exec` (1326–1411)
- `backend/app/agents/dev_agent.py::run_pipeline` (420–460) — sets `_current_gh_token`
- `backend/app/agents/dev_agent.py::_sync_skills_stage` (2432–2495)
- `backend/app/services/session_sandbox_client.py` — URL/header/param plumbing correct
- `backend/app/routes/user.py::get_sandbox_user_token` (530–540)
- `sandbox/server.js` (POST /tasks handler + X-GH-Token middleware + /skills/sync)
- `sandbox/sync-skills.sh`, `sandbox/entrypoint.sh`
- Git: `88558ab` (Phase 4 ACI removal), `fbaa199` (Phase 6 header-only)

**Did NOT change any code.** Per coordination instructions, waiting on Verbal's
complement diagnosis before batching the rebuild/redeploy.

**Learning:** When migrating auth contracts across a process boundary, both
sides need to land in the same release. The middleware change shipped, the
matching handler change didn't. Worth adding a sandbox contract test that
exercises the header-only auth path end-to-end.

## 2025-11-26 — Azure Pipeline Audit Fixes (Commit 2a7e013)

**Scope:** Implemented all four fixes from `.squad/decisions/inbox/fenster-azure-pipeline-audit.md` after Pascal's approval.

**Changes:**
1. **gh-token centralization (BLOCKER)** — Extracted `_maybe_attach_gh_token()` helper. Skills-sync (`_sync_skills_stage`) is now the FIRST sandbox call and attaches `X-GH-Token` on initial request per dev-task. `_sandbox_exec` calls the same helper (no-op if already sent). Preserves dedup set `_gh_token_sent` and teardown logic.

2. **Pool 4xx/5xx surfacing (BLOCKER)** — POST /tasks wrapped in separate try/except for `httpx.HTTPStatusError`. On HTTP error: build diagnostic (status + truncated body), log at ERROR, emit `{"type": "stderr", ...}` to pipeline buffer, re-raise as `RuntimeError`. No more silent fallback to polling with undefined `sandbox_task_id`.

3. **Granular probe errors (HIGH)** — `_probe_sandbox_health()` now returns 4-tuple `(reachable, active, premium, error_detail)`. Catches `HTTPStatusError` (status + body), `ConnectError` ("Pool unreachable (network/DNS issue)"), `TimeoutException` ("Pool cold (no response within 5s)"). `/api/sandbox/start` surfaces `error_detail` in response message. Status polling discards it (transient failures expected).

4. **/api/sandbox/recreate Option B (MED)** — Recreate now enumerates user's dev-tasks via `dev_service.list()`, filters to `{running, provisioning, pending}`, calls `client.stop_session(task_id, reason="recreate")` for each (best-effort). Returns `{"stopped": [ids], "message": "Released N sessions"}`. Frontend button changed from "Recreate" to "Release Sessions".

**Tests added (boundary exception — normally Kobayashi's domain):**
- Updated `test_dev_agent_gh_token.py` (2 new tests: skills-sync first, exec after sync).
- New `test_dev_agent_pool_errors.py` (3 tests: 403, 429, 500).
- New `test_sandbox_probe_errors.py` (4 tests: 403, connect, timeout, start endpoint).
- New `test_sandbox_recreate.py` (3 tests: active sessions, no sessions, error handling).

**Verification:** `pytest` 39 tests green (7 gh_token + 19 session_sandbox_client + 3 disconnect + 3 pool_errors + 4 probe_errors + 3 recreate). `ruff check` + `ruff format` clean on touched files.

**Learnings:**
- When the FIRST sandbox call changes (skills-sync precedes `_sandbox_exec`), the gh-token injection MUST move with it. The dedup tracker is only useful if the helper is called from all entry points.
- Pool errors should always surface to users with actionable diagnostics. The HTTPStatusError → RuntimeError pattern with truncated body (500 chars) + hint ("Check RBAC on session pool resource") is the right trade-off for UX vs log spam.
- `_probe_sandbox_health` returning 4-tuple with optional `error_detail` lets `/start` (user-facing, happens once) show full diagnostics while `/status` (polled every 15s) stays forgiving on transient failures.
- Recreate in pool mode was vestigial because there's no per-user container to rebuild. Stopping active sessions (Option B) is the useful equivalent — next dev-task gets a fresh container from the pool.
- Test organization: respx for HTTP client tests, plain MagicMock + AsyncMock for agent/route logic. Keep assertions on diagnostic strings loose enough to survive minor message tweaks but tight enough to catch regressions (e.g., "HTTP 403" in message, not exact wording).


## 2026-05-26: Azure Pipeline Audit → Fixes Shipped

**Mandate:** Code audit of dev-task pipeline in session-pool mode. Identify blocking issues, silent failure modes.

**Methodology:** Read-only review of commits `c8db9e4`–`909418a`, focusing on `dev_agent.py`, `sandbox.py`, frontend `sandbox-config.tsx`.

**Key Learnings:**

### 7 Findings

**Blockers (2):**
1. Silent HTTPError — pool 4xx/5xx caught but not surfaced. Fallback polling fails (undefined `sandbox_task_id`). User sees no error.
2. gh-token ordering — skills-sync (FIRST call) doesn't attach `X-GH-Token` header. Session allocator receives header on wrong container or not at all.

**High (1):**
3. Start probe error swallowing — bare `except Exception` hides RBAC/network/timeout. User sees generic "stopped".

**Medium (1):**
4. Recreate vestigial — sets "provisioning" status but does nothing in pool mode.

**Low (2):**
5. Status flip-flop — transient probe failures cause UI to flicker.

**OK (2):**
6. Premium baseline tracking preserved.
7. Cosmos lazy upgrade correct.

### Four Fixes Implemented (Commit `2a7e013`)

1. **gh-token → FIRST call** — Centralized `_maybe_attach_gh_token()` helper attached to `_sync_skills_stage` (not later `_sandbox_exec`). Header arrives on actual first allocation.

2. **Surface pool 4xx/5xx errors** — POST /tasks wrapped in own try/except. On error: diagnostic message, log ERROR, emit stderr to output buffer, re-raise as RuntimeError.

3. **Granular start probe errors** — Return 4-tuple from `_probe_sandbox_health()`. Catch HTTPStatusError, ConnectError, TimeoutException separately. `/api/sandbox/start` surfaces error_detail in response message.

4. **Recreate releases sessions (Option B)** — Enumerate active dev-tasks, stop sessions, return stopped list. Frontend button relabeled "Release Sessions".

### Test Coverage (39 tests passing)

- Updated: `test_dev_agent_gh_token.py` (2 new tests)
- New: `test_dev_agent_pool_errors.py` (3 tests)
- New: `test_sandbox_probe_errors.py` (4 tests)
- New: `test_sandbox_recreate.py` (3 tests)

**Boundary exception:** Tests normally Kobayashi's domain, but fixes were tightly coupled to test surface. Flagged for Kobayashi review (coverage, assertion clarity, mock hygiene).

### Production Impact

Silent failures now visible. GitHub PAT primes sandbox on actual first call. Pool errors surface with actionable diagnostics. Recreate releases sessions instead of spinning.

**Expected fix:** Pascal's "no visible error" and "not authenticated" reports should resolve.
- Transient session-pool allocation retry shipped in `_sandbox_exec`: POST `/tasks` now makes 3 total attempts with exponential delays of 1s then 2s between retries (the 4s slot is retained as the next backoff value for the 3-attempt policy) and ±25% jitter to avoid synchronized retry bursts when the pool is cold or capacity constrained. Retry triggers are HTTP 5xx, 429, the exact Azure allocator body substring `Error happened when allocating pod`, allocator-like 5xx `sessionpool` bodies, and `httpx.ConnectError` / `ReadTimeout` / `PoolTimeout`; 4xx except 429 fail immediately.
- Edge case discovered while testing with respx: successful `_sandbox_exec` tests need a fake `stream_response()` context manager after the mocked POST succeeds, otherwise the helper continues into SSE/polling. Repeated respx POST outcomes work cleanly with `side_effect=[Response(...), Response(...), ...]`, and transport exceptions can be mixed into that list before a final success response.

## 2026-05-27 — Session-pool error route gotcha

- The Azure session-pool allocator message `Error happened when allocating pod...` can reach dev-task users through two distinct routes: synchronously as the HTTP response body from backend `POST /tasks`, or asynchronously as sandbox stream/status output after a sandbox task has already been accepted.
- The transient retry added in `986f326` only wraps the synchronous `_sandbox_exec` submit path (`_post_task_with_transient_retry`). It does not inspect `stdout` / `stderr` entries forwarded from `/tasks/{id}/stream` or polling `recentOutput`.
- Current stream handling forwards sandbox entries verbatim into the pipeline buffer before type-specific processing, so any allocator-like text arriving as streamed `stderr` is surfaced to the user without retry/filtering.
- Diagnosis rule: check whether the user-facing text is prefixed by backend `Sandbox pool rejected task (...)` (sync submit path) or appears as raw sandbox stream output (async path). Fix locations differ.


## 2026-05-27 Sandbox Token Cold Cache Recovery

**Context:** After backend redeploy, process-local `_connection_store` token cache was empty. Dev-task `b32637b0` omitted `X-GH-Token` header on first sandbox request → 400 "GitHub token required".

**Root Cause:** `get_sandbox_user_token(user_id)` read ONLY from in-memory `_connection_store` cache. No fallback to Cosmos DB on miss. When cache is lost (redeploy, restart), users hit token-missing errors even though encrypted tokens exist in persistent storage.

**Solution (Commit `9ae0490`):**
- `get_sandbox_user_token(user_id, profile_service)` now: cache-first (O(1) hot path) → cache miss → fallback to `UserProfileService.get_profile(user_id)` from Cosmos DB
- On Cosmos hit: warm cache, decrypt token, emit observability event `sandbox.user_token.cache_miss_recovered`
- Injected `profile_service` into dev agent's `run_pipeline()` so token helper has access to persistent storage

**Implementation Details:**
- In-memory `_connection_store` remains the hot path (no latency penalty for cache hits)
- Cosmos fallback only on miss (expected: rare, cold-start or eviction)
- Structured observability event enables monitoring of cache miss frequency (if high, adjust cache TTL or pre-warm strategy)

**Tests Added:** 
- Cache hit (no Cosmos read)
- Cache miss + Cosmos token present (warm succeeds)
- Cache miss + no Cosmos token (returns None gracefully)

**Learning:** Every service-layer cache with persistent backing MUST have fallback on miss. Critical for multi-turn pipelines and background agents where the process-local cache may have been cleared. Pattern: cache-first (if available) → persistent store fallback → apply side effects (warm cache, log event) → return. This pattern is now standard across NotesService, IdeaService, DevTaskService; apply it consistently to auth-critical helpers like `get_sandbox_user_token()`.

**Decision Created:** `fenster-sandbox-token-cosmos-fallback.md` (merged to decisions.md)
