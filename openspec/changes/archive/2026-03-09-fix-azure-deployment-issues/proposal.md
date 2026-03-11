# Change: Fix Azure Deployment Issues & Add Missing Features

## Why
Multiple issues discovered in the Azure-deployed application affecting dev task pipeline execution, skill storage, dashboard completeness, spec display, and user profile capabilities. Additionally, the lack of structured logging makes debugging these production issues difficult.

## What Changes

### Bug Fixes
1. **Dev task pipeline not executing** — Starting a dev task from a spec creates the task with "running" status but none of the pipeline stages (Plan → Build → Run → Test) actually kick off. The background task execution is not being triggered after task creation in the deployed environment.
2. **Dev task deletion error** — Deleting a dev task returns an error (likely a 500 or missing endpoint issue in production).
3. **Skills stored with default-user** — Skills in Cosmos DB are persisted with `default-user` as the userId instead of the authenticated user's ID. Skill files are also not appearing on Azure Blob Storage.
4. **Spec title shows type suffix** — When creating a spec from an idea, the spec list shows titles like "My App - Foundation" instead of just "My App". The type indicator is redundant since the detail view already shows the Foundation/Feature badge.

### New Features
5. **Dashboard marketing tile** — Add a Marketing summary card to the dashboard alongside Notes, Ideas, Research, and Specs.
6. **Idea-to-spec linking simplification** — Ideas currently show links to both foundation and feature specs. Simplify to only link to the foundational spec (which already contains links to its features).
7. **User profile picture** — Enable users to upload a profile picture via the User Profile page. This picture can be used in marketing video generation to personalize the presenter.
8. **Structured observability logging** — Implement comprehensive structured logging across all backend services for traceability and debugging of production issues.

## Impact
- Affected specs: `dev-service`, `web-app`, `spec-service`, `brainstorm-service`, new `observability`
- Affected code:
  - Backend: `backend/app/services/dev_service.py`, `backend/app/services/brainstorm_service.py`, `backend/app/services/spec_service.py`, `backend/app/routers/`
  - Frontend: `frontend/src/app/`, `frontend/src/components/`
  - Infrastructure: logging configuration, Application Insights integration
