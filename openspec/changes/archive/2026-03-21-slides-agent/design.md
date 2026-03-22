## Context

Turbo Voice Agent is a multi-agent platform where users brainstorm ideas, conduct research, write specs, and develop code — all through voice or manual interaction. The platform currently supports dev-tasks in two modes: "mockup" (single iteration) and "openspec" (multi-iteration with foundation + features). Each dev-task runs inside a sandboxed container with GitHub Copilot CLI.

Users need to present their work to stakeholders but must leave the platform to create presentations. The brainstorm agent pattern (CRUD + AI refinement + voice interaction) is well-established and serves as the template for the new slides agent.

The sandbox infrastructure already supports cloning external repos, running CLI tools, and streaming output. Blob storage is available for file uploads. The deck-engine project (https://github.com/deckio-art/deck-engine) provides a code-based slide generation framework that can run inside the sandbox.

## Goals / Non-Goals

**Goals:**
- Enable users to create, refine, and generate professional slide decks entirely within the platform
- Follow the established brainstorm agent pattern: voice/manual creation → AI refinement → development
- Integrate with existing research for content incorporation
- Provide a streamlined 3-stage dev-task pipeline: init → slides → export
- Export slides to PDF for preview and download
- Add dev-task archiving across all task types for list management

**Non-Goals:**
- Real-time collaborative slide editing (single user per deck)
- Custom slide themes or template marketplace
- Spec linking for slides (explicitly excluded per requirements)
- PowerPoint/Google Slides export formats (PDF only for v1)
- Slide animation or transition support
- Editing generated slides within the platform (edit via re-generation)

## Decisions

### 1. Follow BrainstormAgent pattern exactly
**Decision**: Mirror `brainstorm_agent.py` class structure — `__init__(slides_service)`, `tool_definitions` property, `handle_function_call()` router, `refine()` + `refine_stream()` methods.

**Rationale**: Proven pattern used by 8 other agents. Reduces cognitive load, ensures SupervisorAgent integration works identically. The brainstorm → refine → develop flow maps directly to slides → refine → generate.

**Alternatives**: Custom agent pattern with multi-step wizard — rejected as over-engineered for v1.

### 2. Slides data model stores structured sections
**Decision**: The `Slides` model includes a `sections` field (list of `SlideSection` objects with title, content, notes, image_url) alongside flat description.

**Rationale**: AI refinement produces structured output (ordered sections with content). Storing structure enables section-level editing and precise deck-engine prompt generation. The flat description serves as the initial user input before refinement.

**Alternatives**: Store only flat markdown — rejected because it loses structure needed for accurate slide generation.

### 3. deck-engine cloned fresh per dev-task
**Decision**: During the "init" stage, clone deck-engine into the sandbox workspace. Do not pre-bake it into the sandbox image.

**Rationale**: Ensures latest deck-engine version. Sandbox containers are ephemeral — cloning adds ~10s but avoids image rebuild cycles. Same pattern used for openspec init.

**Alternatives**: Pre-install in sandbox Docker image — rejected due to maintenance burden and version staleness.

### 4. PDF export via headless browser in sandbox
**Decision**: The "export" stage runs the deck-engine dev server inside the sandbox, then uses a headless browser (Playwright) to capture each slide as a page in a single PDF.

**Rationale**: deck-engine produces HTML-based slides. Headless browser capture is the most reliable way to get pixel-perfect PDF output. Playwright is already a project dependency.

**Alternatives**: Server-side PDF generation (puppeteer/wkhtmltopdf) — rejected as Playwright is already available. Direct PDF export from deck-engine — not supported by the framework.

### 5. Dev-task archiving via status field
**Decision**: Add `archived` boolean field to DevTask model. Default `false`. List endpoint accepts `?archived=true` filter. Frontend defaults to showing non-archived tasks.

**Rationale**: Simple, reversible (un-archive). No data deletion. Consistent with how other list views work in the app. Status filtering is already a pattern in the ideas list.

**Alternatives**: Separate archive collection — over-engineered. Soft delete with `deleted_at` — archiving isn't deletion, different semantics.

### 6. Blob storage for exported PDFs
**Decision**: Store exported PDFs in the existing blob storage container under `slides/{task_id}/export.pdf`. Generate SAS URL for preview/download.

**Rationale**: Blob storage already used for marketing videos and skill uploads. Same upload/download pattern. SAS URLs provide time-limited secure access.

### 7. Three-stage pipeline: init → slides → export
**Decision**: Slides dev-tasks use a simplified 3-stage pipeline (no squad, no openspec propose/archive cycles).

**Rationale**: Slide generation is a single-pass task — there's no iterative spec development. The Copilot CLI generates all slides in one pass from the structured description. Fewer stages mean faster turnaround (~2-5 min vs ~15-30 min for spec dev-tasks).

**Alternatives**: Reuse full openspec pipeline — rejected as unnecessary complexity for slide generation.

## Risks / Trade-offs

- **[deck-engine availability]** → External dependency could become unavailable or change API. Mitigation: pin to specific commit/tag in clone command. Consider forking if critical.
- **[PDF quality]** → Headless browser rendering may differ from interactive view. Mitigation: use Playwright with consistent viewport size, test with various content types.
- **[Large presentations]** → Many slides (50+) may slow export. Mitigation: implement progress reporting per-slide during export stage, set reasonable limit in UI (e.g., warn at 30+ slides).
- **[Sandbox timeout]** → deck-engine install + build + export could exceed sandbox timeout. Mitigation: ensure sandbox timeout is sufficient (10 min), report progress during each stage.
- **[Research content size]** → Linked research could be very large, overwhelming the slide prompt. Mitigation: summarize research content before including in generation prompt (same pattern as brainstorm agent's `_gather_research_context`).
