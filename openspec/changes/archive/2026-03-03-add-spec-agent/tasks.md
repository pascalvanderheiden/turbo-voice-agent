## 1. Backend — Models & Service
- [x] 1.1 Create `backend/app/models/spec.py` — Spec, SpecCreate, SpecUpdate Pydantic models
- [x] 1.2 Create `backend/app/services/memory_spec_service.py` — In-memory CRUD with JSON persistence
- [x] 1.3 Create `backend/app/services/spec_service.py` — Cosmos DB CRUD service
- [x] 1.4 Update `backend/app/db/init.py` — Add specs container

## 2. Backend — Agent
- [x] 2.1 Create `backend/app/agents/spec_agent.py` — SpecAgent with tools: create_spec, get_specs, get_spec, update_spec, delete_spec, generate_spec (from idea)
- [x] 2.2 Update `backend/app/agents/supervisor.py` — Register spec agent, add routing for spec functions

## 3. Backend — Routes & Wiring
- [x] 3.1 Create `backend/app/routes/specs.py` — REST routes: GET /api/specs, GET /api/specs/{id}, POST /api/specs, PUT /api/specs/{id}, DELETE /api/specs/{id}, POST /api/specs/generate
- [x] 3.2 Update `backend/app/main.py` — Wire spec service, agent, routes
- [x] 3.3 Update `backend/app/voice/session.py` — Add spec capabilities to voice instructions and greetings

## 4. Frontend — API & i18n
- [x] 4.1 Update `frontend/src/lib/api.ts` — Add Spec types and specsApi methods
- [x] 4.2 Update `frontend/src/lib/i18n.tsx` — Add spec translation keys (EN/NL)

## 5. Frontend — Pages & Navigation
- [x] 5.1 Create `frontend/src/app/(app)/specs/page.tsx` — Specs page with list, create/edit/delete dialogs, detail view with optimized content
- [x] 5.2 Update `frontend/src/app/(app)/ideas/page.tsx` — Add "Convert to spec" button in idea detail view
- [x] 5.3 Update `frontend/src/components/layout/app-sidebar.tsx` — Add Specs nav item
- [x] 5.4 Update `frontend/src/app/(app)/dashboard/page.tsx` — Add Specs card
- [x] 5.5 Update `frontend/src/app/(app)/voice/page.tsx` — Add spec action labels for notifications

## 6. Backend — Agent Status
- [x] 6.1 Update `backend/app/main.py` — Add spec agent to /api/agents/status endpoint
