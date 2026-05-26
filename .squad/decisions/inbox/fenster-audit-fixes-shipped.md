# Azure Pipeline Audit — Fixes Shipped

**Date:** 2025-11-26  
**Agent:** Fenster (Backend Dev)  
**Commit:** `2a7e013`  
**Approved by:** Pascal

---

## Summary

All four fixes from `.squad/decisions/inbox/fenster-azure-pipeline-audit.md` have been implemented and tested.

---

## Changes Delivered

### Fix 1 (BLOCKER) — gh-token attached to FIRST sandbox call

**Problem:** Skills-sync ran before `_sandbox_exec` but didn't attach `X-GH-Token`, so the session allocator sometimes landed on a container without gh-auth.

**Implementation:**
- Extracted centralized helper `_maybe_attach_gh_token(task_id, headers)` that checks `_gh_token_sent` and adds the header if needed.
- `_sync_skills_stage` now calls the helper and attaches `X-GH-Token` on the first call.
- `_sandbox_exec` also calls the same helper (no-op if skills-sync already ran for that task).

**Files:**
- `backend/app/agents/dev_agent.py` (lines 2432–2450)

---

### Fix 2 (BLOCKER) — surface pool 4xx/5xx errors

**Problem:** `_sandbox_exec` POST /tasks → httpx.HTTPStatusError caught by outer try/except, fell back to polling, but `sandbox_task_id` was never assigned → empty output, user saw nothing.

**Implementation:**
- Wrapped POST /tasks in its own try/except that catches `httpx.HTTPStatusError` specifically.
- On HTTP error: build diagnostic message (status + truncated body), log at ERROR, emit `{"type": "stderr", ...}` into pipeline output buffer, then re-raise as `RuntimeError`.

**Files:**
- `backend/app/agents/dev_agent.py` (lines 1403–1428)

---

### Fix 3 (HIGH) — granular error reporting in /api/sandbox/start probe

**Problem:** `_probe_sandbox_health` bare `except Exception:` hid RBAC/network/timeout root cause; UI showed generic "stopped".

**Implementation:**
- Changed `_probe_sandbox_health` to return 4-tuple: `(reachable, active, premium, error_detail | None)`.
- Catch separately: `httpx.HTTPStatusError` (include status + truncated body), `httpx.ConnectError` ("Pool unreachable (network/DNS issue)"), `httpx.TimeoutException` ("Pool cold (no response within 5s)").
- Updated `/api/sandbox/start` to surface `error_detail` in response `message` field.
- `/api/sandbox/status` caller updated to accept 4-tuple (error_detail discarded for polling — only `/start` needs it).

**Files:**
- `backend/app/routes/sandbox.py` (lines 44–87, 99, 265–278)

---

### Fix 4 (MED) — /api/sandbox/recreate releases user sessions (Option B)

**Problem:** Recreate did nothing in pool mode — set status to "provisioning" but never cleared any session state.

**Implementation (Option B per Pascal's choice):**
- Enumerate user's dev-tasks via `dev_service.with_user(user_id).list()`.
- Filter to tasks in `{running, provisioning, pending}` (may hold active sessions).
- For each, call `client.stop_session(task_id, reason="recreate")` (best-effort — log + continue on error).
- Return `{"status": "ready", "stopped": [task_ids], "message": "Released N session(s)"}`.
- Frontend button label changed from "Recreate" to "Release Sessions" with tooltip.

**Files:**
- `backend/app/routes/sandbox.py` (lines 158–199)
- `frontend/src/components/agents/sandbox-config.tsx` (lines 210–217)

---

## Tests Added (Boundary Exception)

Per task instructions, these test updates were included in this commit even though tests are normally Kobayashi's domain:

### Updated:
- `backend/tests/test_dev_agent_gh_token.py`:
  - Added `test_skills_sync_attaches_x_gh_token_first` — verifies skills-sync is first call and attaches header.
  - Added `test_sandbox_exec_after_skills_sync_omits_token` — verifies exec sees task in tracker and omits header.

### New:
- `backend/tests/test_dev_agent_pool_errors.py` (3 tests):
  - `test_http_403_raises_runtime_error_with_diagnostic` — 403 → RuntimeError with RBAC hint.
  - `test_http_429_raises_runtime_error_with_diagnostic` — 429 → RuntimeError with concurrency message.
  - `test_http_500_raises_runtime_error` — 500 → RuntimeError with truncated body.

- `backend/tests/test_sandbox_probe_errors.py` (4 tests):
  - `test_probe_http_403_returns_error_detail` — probe 403 → error_detail includes status + body.
  - `test_probe_connect_error_returns_network_message` — ConnectError → "Pool unreachable".
  - `test_probe_timeout_returns_cold_message` — TimeoutException → "Pool cold".
  - `test_start_endpoint_surfaces_error_detail` — POST /start → error_detail in response message.

- `backend/tests/test_sandbox_recreate.py` (3 tests):
  - `test_recreate_stops_active_user_sessions` — recreate stops tasks in {running, provisioning, pending}.
  - `test_recreate_handles_no_active_tasks` — recreate with zero tasks returns appropriate message.
  - `test_recreate_continues_on_stop_failure` — recreate logs error but continues for remaining tasks.

---

## Verification

```bash
cd backend && source .venv/bin/activate
ruff check app/agents/dev_agent.py app/routes/sandbox.py  # ✅ clean
ruff format app/agents/dev_agent.py app/routes/sandbox.py tests/  # ✅ formatted

pytest tests/test_dev_agent_gh_token.py \
       tests/test_session_sandbox_client.py \
       tests/test_sandbox_disconnect.py \
       tests/test_dev_agent_pool_errors.py \
       tests/test_sandbox_probe_errors.py \
       tests/test_sandbox_recreate.py -v

# ✅ 39 passed in 1.09s
```

---

## Notes for Kobayashi

The boundary exception allowed me to update tests directly for this single commit because the fixes were tightly coupled to the test surface. All new tests:
- Follow existing patterns from `test_dev_agent_gh_token.py` and `test_session_sandbox_client.py`.
- Use respx for HTTP mocking (when applicable) or plain MagicMock/AsyncMock.
- Are fast (< 0.5s each).

Please review:
1. Test coverage completeness (any edge cases I missed?).
2. Assertion clarity (are diagnostic message checks too brittle?).
3. Mock hygiene (any leaking state across tests?).

---

## Outcome

**All four fixes shipped.** Commit `2a7e013` resolves the silent failure modes identified in the audit:
- GitHub PAT now primes the sandbox on the ACTUAL first call.
- Pool errors surface to the user with actionable diagnostics.
- Recreate now does something useful (releases active sessions).

Next steps:
- Monitor for RBAC 403s in production logs (should now be user-visible).
- Verify skills-sync → gh-auth flow in Azure (expected to fix Pascal's "not authenticated" reports).
