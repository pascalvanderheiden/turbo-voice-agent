# Fenster — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI backend, Cosmos DB, Azure Voice Live API.
User: the project maintainer.

Backend has 12 specialist agents: notes, brainstorm, research, spec, dev, marketing, slides, skills, todo, work + supervisor. Service layer pattern with dual Cosmos DB + InMemory implementations.

## Team Updates

- **2026-05-22:** Verbal diagnosed and recovered failed `azd up` deployment. Root cause: Bicep RBAC module dependency ordering catch-22 — backend Container App identity had zero role assignments because RBAC module depends on backend being healthy, creating circular dependency. Manual fix: `az role assignment create` granted AcrPull to backend identity. **Action required:** Run `azd provision` then `azd deploy` to complete deployment. Permanent fix: Two-phase RBAC Bicep refactor proposed (see `.squad/decisions/decisions.md`).
- **2026-05-20:** Verbal deployed quota-aware region selector (`infra/scripts/select-model-regions.sh`) as `azd` preprovision hook. Three new env vars in CI/CD pipelines: `AZURE_OPENAI_LOCATION_PRIMARY`, `AZURE_OPENAI_LOCATION_VOICE`, `AZURE_OPENAI_LOCATION_RESEARCH`. This resolves fresh `azd up` quota failures on new subscriptions and enables interactive region selection for multi-region deployments.

## Learnings
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
