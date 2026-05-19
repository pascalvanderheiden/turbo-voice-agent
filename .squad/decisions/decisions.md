# Team Decisions

## Redfoot — OSS Release: Open-Source Preparation Strategy

**Author:** Redfoot  
**Date:** 2026-03-29  
**Status:** Proposed (pending approval)

### Decision

The project will be prepared for open-source release following a comprehensive audit and scrubbing process that ensures no personal identifiers, credentials, or environment-specific configuration remain in the codebase or git history.

### Key Choices

1. **MIT License** — Selected MIT over Apache 2.0 or GPL for its simplicity and permissiveness, aligning with reference implementation goals.
2. **Decommission-Then-Redeploy Validation** — Existing Azure deployment will be torn down via `azd down --force --purge` and redeployed from scratch to validate that instructions work end-to-end for new users.
3. **Multi-Pass Scrubbing Strategy** — Automated grep searches for known patterns (names, emails, GUIDs) combined with manual audit of high-risk files (Bicep, workflows, env examples).
4. **Parameter-First Infrastructure** — All Bicep templates will use parameters declared in `azure.yaml` with no hardcoded personal values. Required parameters documented with descriptions.
5. **README as Primary Onboarding** — Complete README rewrite structured for deployment (manual + automated) as the primary user journey, with local development as secondary.
6. **.squad/ Folder Treatment** — `.squad/` folder will remain in repository but documented as project-specific local metadata (safe to ignore for new users).
7. **GitHub Actions Workflow Preserved** — Existing CI/CD workflow kept as-is, with all personal values extracted to repository variables that users configure post-fork.

### Impact

- **Documentation:** Major README rewrite, addition of 3 governance documents (LICENSE, CODE_OF_CONDUCT.md, SECURITY.md)
- **Infrastructure:** All Bicep files must be audited and parameterized
- **Timeline:** Decommission scheduled as final step before repository goes public (minimize downtime)
- **Risk:** If redeployment fails, OSS release delayed until instructions validated

---

## Kobayashi — Slides pipeline test note

**Date:** 2026-05-19

I updated the slides-stage regression coverage in tests only.

- `backend/tests/test_slides_service.py` now verifies slides-mode tasks expose exactly three stages drawn from `init`, `slides`, and `run`.
- The backend assertion explicitly rejects the removed `skills` stage.
- The assertion is set-based instead of order-based because the current service still emits `run` before `slides`; this keeps the regression focused on the stage rename/removal requested in task 7.4 without changing production code from the tester role.
- `frontend/e2e/dev-task-e2e.spec.ts` now expects the visible slides labels `Init`, `Slides`, and `Run`.

Follow-up for implementers: if stage order matters contractually, production code still needs a separate fix to emit `init → slides → run` consistently.
