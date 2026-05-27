# Kobayashi — History

## Project Context
Turbo Voice Agent — testing and quality.
Stack: pytest (backend), Playwright (E2E), Jest + React Native Testing Library (mobile).
User: the project maintainer.

Testing covers backend services, agent behavior, frontend E2E, and mobile. Target ≥80% coverage on service layers.

## Learnings
- 2026-05-19: Updated `backend/tests/test_slides_service.py`, `frontend/e2e/dev-task-e2e.spec.ts`, and `openspec/changes/optimize-slides-pipeline/tasks.md` for the slides pipeline rename. Backend coverage now checks slides-mode tasks expose exactly three stages drawn from `init`, `slides`, and `run`, and explicitly rejects `skills`.
- 2026-05-19: Local backend pytest execution needed a project venv with `pytest-asyncio`; use `cd backend && . .venv/bin/activate && pytest tests/test_slides_service.py -v` when validating async service tests on this repo.

## 2026-05-22T12:32:51Z — Phase 9 local test sweep (sandbox-dynamic-sessions)

Ran 9.1/9.2/9.3/9.6 locally for Pascal; deferred 9.4/9.5 (azd up + cold-start) per instruction.

**Results:**
- Backend pytest: 99 pass / 18 fail / 5 skip. **All 36 sandbox-migration tests green** (SessionSandboxClient 19, sandbox_service 6, sandbox_auth 3, sandbox_disconnect 3, dev_agent_gh_token 5). 18 failures are pre-existing Entra-auth (notes/todo modules) — unrelated to session-pool work.
- Backend lint: sandbox-touched files cleaned with trivial `ruff check --fix` + `ruff format` (3 files, +4/-7). Repo-wide 259 ruff errors + 51 format-pending files are pre-existing debt — flagged for a separate housekeeping change.
- Frontend lint: hangs on first run because `next lint` (deprecated in Next 16) prompts to install ESLint and no `.eslintrc.json` is checked in. Pre-existing infra gap. Reverted accidental config install to keep tree clean.
- Playwright dev-task spec exists (`e2e/dev-task-e2e.spec.ts`) but targets the deployed Azure backend with MSAL token — it's a deployed-env verification spec, not a local smoke. Cannot run pre-deploy.
- `openspec status` → 4/4 artifacts, apply-ready.

**Learnings:**
- `frontend/e2e/dev-task-e2e.spec.ts` is the post-deploy UI verification harness for the dev-task pipeline (mockup/slides modes, archive flow, status panel). Re-use after every `azd deploy` that touches dev-task code paths.
- Frontend ESLint config is missing from this repo. If we ever need a real `npm run lint`, it has to be set up first (Next 16 wants the new `eslint.config.mjs`).
- Repo-wide ruff debt is real but stable — touching it inside a feature change muddies the diff. Keep lint cleanup as its own PR.
- When running interactive CLIs in agent mode, watch for hidden prompts (`next lint` was waiting silently for ESLint config selection — looked like a hang).
- Pattern for verifying scoped-change health amid pre-existing failures: re-run the targeted test subset (sandbox files only) to confirm zero regressions, then document the pre-existing failure set verbatim. Don't try to fix orthogonal debt.

**Recommendation given:** 🟢 Pascal cleared to run `azd up` for 9.4/9.5 validation wave. No new regressions; all sandbox-specific paths green.

## 2026-05-26: Boundary Exception — Fenster Test Coverage for Audit Fixes

**Context:** Fenster-1 completed Azure pipeline audit, identifying 2 BLOCKERS and 1 HIGH + 1 MED + 2 LOW findings. Fenster-fix implemented all four priority fixes (gh-token ordering, surface pool errors, probe error handling, recreate sessions).

**Boundary Exception Applied:** Fenster-fix included test implementation for this commit (normally Kobayashi's domain) because:
1. Fixes tightly coupled to test surface (mocking sandbox errors, probe failures, session stops)
2. All tests follow existing patterns (respx for HTTP mocking, AsyncMock/MagicMock)
3. Fast execution (~0.5s each), no flaky tests
4. 39 total tests, all passing

**Tests Added:**
- `test_dev_agent_gh_token.py` (2 tests): skills-sync header attachment, exec skips repeated token
- `test_dev_agent_pool_errors.py` (3 tests): 403, 429, 500 HTTP error diagnostics + RuntimeError
- `test_sandbox_probe_errors.py` (4 tests): probe HTTP error detail, network error, timeout error, endpoint surface
- `test_sandbox_recreate.py` (3 tests): stop active sessions, no-op with zero tasks, error handling

**Request for Kobayashi Review:**
1. **Coverage:** Any edge cases I missed? Are the diagnostic message checks too brittle?
2. **Assertion clarity:** Do error message checks match production behavior well enough?
3. **Mock hygiene:** Any leaking state across tests? Respx cleanup adequate?

**Commit:** `2a7e013` (includes tests + implementation).

**Next:** Once Kobayashi reviews, fenster-fix commit ready for merge. Phase 9 local test sweep (Kobayashi's e2e suite) can proceed with fixes deployed.

- **2026-05-27:** Redfoot archived `sandbox-dynamic-sessions` OpenSpec change (49/50 tasks complete, production verified). See `.squad/decisions/decisions.md`.
