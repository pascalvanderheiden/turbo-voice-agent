## 1. Backend — Data Models & Service
- [x] 1.1 Create `backend/app/models/dev_task.py` with DevTask, DevTaskCreate, DevStage, DevArtifact Pydantic models
- [x] 1.2 Create `backend/app/services/dev_service.py` with CRUD + stage transition methods + JSON persistence
- [x] 1.3 Create `backend/app/routes/dev.py` with REST endpoints (list, get, create, delete, trigger pipeline)

## 2. Backend — Turbo Dev Agent
- [x] 2.1 Create `backend/app/agents/dev_agent.py` with tool definitions (create_dev_task, get_dev_tasks, get_dev_task, delete_dev_task, trigger_dev_pipeline)
- [x] 2.2 Integrate GitHub Copilot SDK with gpt-5.3-codex for code generation in Plan + Build stages
- [x] 2.3 Integrate Playwright MCP server for Run + Test stages (start dev server, take snapshots, verify build)
- [x] 2.4 Implement 4-stage background pipeline: Plan → Build → Run → Test with per-stage status updates
- [x] 2.5 Store artifacts: screenshots (base64 in model), compressed code (.tar.gz in `.data/dev/`)

## 3. Backend — Agent Registration
- [x] 3.1 Register Turbo Dev Agent in supervisor with dev_* function routing
- [x] 3.2 Update `backend/app/main.py` to init dev service, dev agent, register routes, update agent topology
- [x] 3.3 Update voice session instructions to include dev agent capabilities
- [x] 3.4 Update chat system prompt to include dev agent capabilities

## 4. Frontend — Development Pages
- [x] 4.1 Create `frontend/src/app/(app)/development/page.tsx` — task list with status badges, pipeline stage indicators
- [x] 4.2 Create `frontend/src/app/(app)/development/[id]/page.tsx` — detail view with stage progress, artifacts (screenshots), logs
- [x] 4.3 Create development task creation dialog (select spec, optional title override)
- [x] 4.4 Add Development to sidebar navigation with Code icon
- [x] 4.5 Add i18n translations for development pages (EN + NL)
- [x] 4.6 Add devApi to `frontend/src/lib/api.ts` with all endpoints

## 5. Frontend — Dashboard Integration
- [x] 5.1 Add development task count/status to dashboard cards
- [x] 5.2 Add pipeline stage progress visualization component

## 6. Mobile — Development Screens
- [x] 6.1 Add development list screen accessible from More menu
- [x] 6.2 Add development detail screen with stage progress
- [x] 6.3 Add devApi to `mobile/src/lib/api.ts`

## 7. Testing & Verification
- [x] 7.1 Verify backend starts without errors with new routes and agent
- [x] 7.2 Verify frontend builds and renders development pages
- [x] 7.3 Test manual dev task creation via UI
- [x] 7.4 Test pipeline execution end-to-end (Plan → Build → Run → Test)
- [x] 7.5 Verify agent topology shows Turbo Dev as 5th specialist
