# Kobayashi — History

## Project Context
Turbo Voice Agent — testing and quality.
Stack: pytest (backend), Playwright (E2E), Jest + React Native Testing Library (mobile).
User: the project maintainer.

Testing covers backend services, agent behavior, frontend E2E, and mobile. Target ≥80% coverage on service layers.

## Learnings
- 2026-05-19: Updated `backend/tests/test_slides_service.py`, `frontend/e2e/dev-task-e2e.spec.ts`, and `openspec/changes/optimize-slides-pipeline/tasks.md` for the slides pipeline rename. Backend coverage now checks slides-mode tasks expose exactly three stages drawn from `init`, `slides`, and `run`, and explicitly rejects `skills`.
- 2026-05-19: Local backend pytest execution needed a project venv with `pytest-asyncio`; use `cd backend && . .venv/bin/activate && pytest tests/test_slides_service.py -v` when validating async service tests on this repo.
