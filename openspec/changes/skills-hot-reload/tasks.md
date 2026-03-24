## 1. Sandbox Endpoints

- [ ] 1.1 Add `POST /skills/sync` endpoint to `sandbox/server.js` — runs the blob sync logic (same as entrypoint.sh) and returns `{ synced: N }`. Handle missing `AZURE_STORAGE_ACCOUNT_NAME` gracefully.
- [ ] 1.2 Add `DELETE /skills/:name` endpoint to `sandbox/server.js` — removes `/home/agent/.copilot/skills/:name/` directory and returns `{ deleted: name }`. Idempotent if directory doesn't exist.
- [ ] 1.3 Extract the blob sync bash logic from `sandbox/entrypoint.sh` into a reusable shell script (`sandbox/sync-skills.sh`) so both the entrypoint and the `/skills/sync` endpoint can call it.

## 2. Backend Push Integration

- [ ] 2.1 Add a `_sync_sandbox_skills()` helper in `backend/app/main.py` that calls `POST {SANDBOX_URL}/skills/sync`. Best-effort: log warning on failure, don't raise.
- [ ] 2.2 Call `_sync_sandbox_skills()` at the end of the `POST /api/agents/skills/install` endpoint (after blob upload).
- [ ] 2.3 Call `DELETE {SANDBOX_URL}/skills/{name}` at the end of the `DELETE /api/agents/skills/{name}` endpoint (after blob + Cosmos cleanup). Best-effort.
- [ ] 2.4 Call `_sync_sandbox_skills()` at the end of `POST /api/dev/skills/upload-local` (after blob upload).

## 3. Remove Per-Task Skills Stage

- [ ] 3.1 Remove the "skills" stage from the mockup pipeline in `dev_agent.py` (~lines 422-434): remove `set_iteration_stage_status` calls for "skills" and the `_install_skills_in_sandbox` call.
- [ ] 3.2 Remove the "skills" stage from the sequential pipeline in `dev_agent.py` (~lines 548-555): same removal.
- [ ] 3.3 Remove `_install_skills_in_sandbox()` method entirely from `dev_agent.py`.
- [ ] 3.4 Remove `_verify_skills_in_sandbox()` method entirely from `dev_agent.py`.

## 4. Frontend Pipeline Stage Cleanup

- [ ] 4.1 Remove "skills" from `FOUNDATION_STAGES` array in `frontend/src/app/(app)/development/[id]/page.tsx` (line ~100).
- [ ] 4.2 Verify no other frontend code references the "skills" stage name; remove any related UI elements.

## 5. Verification

- [ ] 5.1 Test: activate a marketplace skill → verify it appears in sandbox `/home/agent/.copilot/skills/` without starting a dev-task.
- [ ] 5.2 Test: deactivate a skill → verify it's removed from sandbox immediately.
- [ ] 5.3 Test: run a mockup dev-task → verify no "skills" stage in pipeline output.
- [ ] 5.4 Compile check backend (`python -m py_compile app/agents/dev_agent.py`) and frontend (`npx tsc --noEmit`).
