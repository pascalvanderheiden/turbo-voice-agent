## 1. Slides Data Model & Service

- [x] 1.1 Create `backend/app/models/slides.py` with SlideSection, SlidesBase, SlidesCreate, SlidesUpdate, Slides models (title, description, sections, images, attachments, status, refined_draft)
- [x] 1.2 Create `backend/app/services/slides_service.py` (Cosmos DB) with CRUD methods, with_user(), set_refined(), docType="slides"
- [x] 1.3 Create `backend/app/services/memory_slides_service.py` (InMemory fallback) mirroring BrainstormService pattern
- [x] 1.4 Add slides service initialization in `backend/app/main.py` lifespan (both Cosmos and InMemory paths)

## 2. Slides Agent

- [x] 2.1 Create `backend/app/agents/slides_agent.py` with SlidesAgent class: __init__, tool_definitions (create_slides, get_slides_list, get_slides, update_slides, delete_slides, refine_slides), handle_function_call
- [x] 2.2 Add refine() and refine_stream() methods with AI prompt for structured slide section generation, research context gathering, file content extraction
- [x] 2.3 Register SlidesAgent in `backend/app/agents/supervisor.py` — add to agent registry, wire tool routing

## 3. Slides API Routes

- [x] 3.1 Create `backend/app/routes/slides.py` with endpoints: GET/POST /api/slides, GET/PUT/DELETE /api/slides/{id}, POST /api/slides/{id}/refine, POST /api/slides/{id}/refine/stream, GET /api/slides/{id}/research
- [x] 3.2 Wire slides routes in `backend/app/main.py` (include router, set service refs)
- [x] 3.3 Add slides API client functions in `frontend/src/lib/api.ts` (slidesApi object with list, get, create, update, delete, refine, refineStream)

## 4. Slides Frontend Page

- [x] 4.1 Create `frontend/src/app/(app)/slides/page.tsx` — list view with cards, create dialog, detail view with sections editor, file upload, research linking
- [x] 4.2 Add refine button and streaming refinement UI (re-refine support for already refined presentations)
- [x] 4.3 Add slides navigation item in sidebar/layout
- [x] 4.4 Add slide section editor component — reorder sections, edit title/content/notes per section

## 5. Slides Dev-Task Pipeline

- [x] 5.1 Add "slides" mode to DevTask model in `backend/app/models/dev_task.py` — add mode literal, artifacts field (pdfUrl, codeUrl), archived boolean
- [x] 5.2 Create `_run_slides_pipeline()` in `backend/app/agents/dev_agent.py` — 3 stages: init (clone deck-engine, install deps), slides (Copilot CLI generates deck), export (headless browser PDF capture)
- [x] 5.3 Wire slides pipeline routing in dev_agent.py — add mode="slides" check alongside mockup/openspec
- [x] 5.4 Add export stage: start deck-engine dev server, use Playwright to capture each slide page to PDF, combine, upload to blob storage

## 6. PDF Preview & Download

- [x] 6.1 Add PDF preview component in dev-task detail — embedded viewer with page navigation, shown after export stage completes
- [x] 6.2 Add PDF download button in dev-task detail for completed slides tasks
- [x] 6.3 Add source code download endpoint — zip workspace and serve for download
- [x] 6.4 Store artifact URLs (pdfUrl, codeUrl) on dev-task after export completion

## 7. Dev-Task Archiving

- [x] 7.1 Add archived boolean field to DevTask model (default false), update Cosmos queries for archive filter
- [x] 7.2 Add PATCH /api/dev/tasks/{id}/archive and /unarchive endpoints
- [x] 7.3 Add archive filter UI in dev-task list — "Active" (default), "Archived", "All" tabs/buttons
- [x] 7.4 Add archive/unarchive buttons on dev-task cards and detail view header

## 8. Testing & Integration

- [x] 8.1 Add backend tests for slides service CRUD and refinement
- [x] 8.2 Add backend tests for slides agent tool routing
- [x] 8.3 Add backend tests for dev-task archiving endpoints
- [x] 8.4 Verify slides pipeline stages execute correctly in sandbox
- [x] 8.5 Test PDF export and blob storage upload end-to-end
