# Team Decisions

## Kobayashi — Slides pipeline test note

**Date:** 2026-05-19

I updated the slides-stage regression coverage in tests only.

- `backend/tests/test_slides_service.py` now verifies slides-mode tasks expose exactly three stages drawn from `init`, `slides`, and `run`.
- The backend assertion explicitly rejects the removed `skills` stage.
- The assertion is set-based instead of order-based because the current service still emits `run` before `slides`; this keeps the regression focused on the stage rename/removal requested in task 7.4 without changing production code from the tester role.
- `frontend/e2e/dev-task-e2e.spec.ts` now expects the visible slides labels `Init`, `Slides`, and `Run`.

Follow-up for implementers: if stage order matters contractually, production code still needs a separate fix to emit `init → slides → run` consistently.
