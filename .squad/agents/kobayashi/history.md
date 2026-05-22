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
