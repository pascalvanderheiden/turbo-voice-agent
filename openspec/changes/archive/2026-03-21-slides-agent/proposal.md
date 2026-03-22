## Why

The platform supports brainstorming ideas, writing specs, and developing code — but lacks a way to create professional slide presentations. Users need to present their ideas, research findings, and project progress to stakeholders. Currently they must leave the platform and use separate tools (PowerPoint, Google Slides) losing context and integration with their research and ideas. Adding a Slides Agent enables end-to-end workflow: ideate → research → present — all within Turbo Agent.

## What Changes

- **New Slides Agent**: A specialist agent (similar to BrainstormAgent) that guides users through slide deck creation via voice or manual input
- **Slides CRUD service**: Full data model with title, description, structured sections, file attachments (images/PDFs for styling context), and linked research
- **AI-powered slide refinement**: Users describe their presentation, AI proposes a structured slide setup with sections, then refines based on feedback
- **Research linking**: Incorporate completed research into slide content (no spec linking needed)
- **Slidedeck dev-task mode**: A new dev-task pipeline type "slides" with 3 stages: init (scaffold deck-engine project), slides (generate slides via Copilot CLI), export (render pages to PDF)
- **deck-engine integration**: Uses [deck-engine](https://github.com/deckio-art/deck-engine) as the slide generation framework inside the sandbox
- **PDF export & preview**: Export each slide page to PDF, store in blob storage, preview directly in the dev-task detail view
- **Code & PDF download**: Users can download the generated deck-engine source code and the exported PDF
- **Dev-task archiving**: Add status-based archiving for all dev-task types (specs and slides), with filtering — default view shows active tasks only

## Capabilities

### New Capabilities
- `slides-service`: CRUD for slide presentations — create, list, update, delete, refine with AI, link research, upload images/PDFs for context
- `slides-agent`: Specialist agent with tool definitions for slide management, registered in SupervisorAgent routing
- `slides-pipeline`: Dev-task pipeline mode "slides" with stages: init → slides → export, using deck-engine in sandbox
- `slides-export`: PDF export from deck-engine, blob storage upload, in-app preview and download
- `dev-task-archiving`: Status-based archiving for dev-tasks (active/archived), filter in list view, default shows active

### Modified Capabilities
- `dev-service`: Add "slides" mode to dev-task creation and pipeline routing, add archived status field
- `agent-orchestration`: Register SlidesAgent in SupervisorAgent, add routing for slides tool calls

## Impact

- **Backend**: New agent (`slides_agent.py`), model (`slides.py`), service (`slides_service.py`, `memory_slides_service.py`), routes (`slides.py`). Modify `dev_agent.py` (new pipeline), `supervisor.py` (new agent registration), `dev_service.py` (archived status)
- **Frontend**: New slides page (`/slides`), slides API client, slides detail view with section editor and file uploads. Modify dev-task list (archive filter), dev-task detail (PDF preview). Add slides nav item
- **Infrastructure**: deck-engine repo cloned in sandbox during init stage. Blob storage used for PDF exports (existing infra)
- **Dependencies**: deck-engine (https://github.com/deckio-art/deck-engine) — used inside sandbox only, no backend dependency
- **Database**: New Cosmos DB document type `"slides"` in existing container, new `"archived"` status for dev-tasks
