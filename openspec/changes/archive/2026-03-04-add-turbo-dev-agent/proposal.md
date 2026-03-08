# Change: Add Turbo Dev Agent with Development Task Tracking

## Why
Users need the ability to turn registered specs into working frontend applications. A new "Turbo Dev" agent — powered by the GitHub Copilot SDK with gpt-5.3-codex and Playwright MCP for testing — will plan, build, run, and test a spec-based application. Development tasks track progress through four pipeline stages (Plan → Build → Run → Test), similar to how research entries track background work. Users can also create development tasks manually.

## What Changes
- **New capability**: `dev-service` — Development task CRUD, 4-stage pipeline (Plan, Build, Run, Test), background task execution, artifact storage (screenshots, compressed code)
- **New agent**: Turbo Dev Agent registered as a specialist in the agent team, using GitHub Copilot SDK with Playwright MCP server attached, powered by gpt-5.3-codex
- **Modified capability**: `agent-orchestration` — Supervisor routes dev_* functions to the new Turbo Dev Agent
- **Modified capability**: `web-app` — New "Development" page with task list, detail view, manual creation, pipeline progress visualization
- **Modified capability**: `mobile-app` — Development screen accessible from More menu

## Impact
- Affected specs: `dev-service` (new), `agent-orchestration`, `web-app`, `mobile-app`
- Affected code:
  - `backend/app/models/dev_task.py` — New Pydantic models
  - `backend/app/services/dev_service.py` — Dev task service with pipeline execution
  - `backend/app/routes/dev.py` — REST API endpoints
  - `backend/app/agents/dev_agent.py` — Turbo Dev Agent (Copilot SDK + Playwright MCP)
  - `backend/app/main.py` — Register dev agent, routes, agent topology
  - `frontend/src/app/(app)/development/` — Development pages
  - `frontend/src/lib/api.ts` — Dev API client
  - `frontend/src/lib/i18n.tsx` — Translations
  - `frontend/src/components/layout/app-sidebar.tsx` — Nav entry
  - `mobile/app/` — Development screens
  - `mobile/src/lib/api.ts` — Mobile API layer
