## Tasks

### Group 1: Models & Service Layer

- [x] **1.1 Update Slides model** — Add `subtitle: str = ""`, `icon: str = ""`, `theme: str = "shadcn/ui"`, `appearance: str = "dark"`, `palette: str = "arctic"` fields. Remove `images: list[str] = []`. Keep `attachments` but validate `.pptx` only.
  Files: `backend/app/models/slides.py`

- [x] **1.2 Update SlidesCreate/SlidesUpdate** — Add deck config fields to create/update schemas. Remove images from SlidesUpdate.
  Files: `backend/app/models/slides.py`

- [x] **1.3 Validate PowerPoint-only attachments** — Add validation in slides routes to reject non-`.pptx` files. Return 400 with message "Only .pptx files are accepted as attachments."
  Files: `backend/app/routes/slides.py`

### Group 2: Slides Agent — Refinement

- [x] **2.1 Rewrite REFINE_SYSTEM_PROMPT** — New prompt that produces: (1) `## Deck Config` YAML block (title, subtitle, icon, theme, appearance, palette) and (2) `## Slides` numbered list with title + max 2 sentences per slide. Drop verbose design recommendations section.
  Files: `backend/app/agents/slides_agent.py`

- [x] **2.2 Parse deck config from refined output** — After refinement, extract Deck Config fields from the refined_draft and populate the Slides model's deck config fields (subtitle, icon, theme, appearance, palette).
  Files: `backend/app/agents/slides_agent.py`

### Group 3: Dev Agent — Pipeline Rewrite

- [x] **3.1 Parse deck config in slides pipeline init** — In `_run_slides_pipeline()`, parse the Deck Config YAML from the slides spec's refined_draft. Use parsed values for `npx create-deckio` arguments instead of hardcoded values.
  Files: `backend/app/agents/dev_agent.py`
  Depends on: 2.1

- [x] **3.2 Rewrite slides stage to single autopilot invocation** — Replace slide-by-slide iteration with one `copilot --experimental --yolo --autopilot --model <model> --agent squad -p "<full slides content>"` call. Extract the Slides section from the refined draft as the prompt.
  Files: `backend/app/agents/dev_agent.py`

- [x] **3.3 Add PowerPoint template porting** — After the main slides invocation, check if the slides spec has `.pptx` attachments. If so, run `copilot --continue -p "/deck-port-powerpoint <blob-url>"` for the first attachment.
  Files: `backend/app/agents/dev_agent.py`
  Depends on: 3.2

- [x] **3.4 Rewrite export to screenshots** — Replace PDF export with: `npm run dev` → Playwright screenshots of each slide route → upload via existing `_collect_screenshots()` mechanism. Remove PDF blob storage upload.
  Files: `backend/app/agents/dev_agent.py`

### Group 4: Run Live Feature

- [x] **4.1 Add sandbox live preview endpoint** — New endpoint `POST /api/dev/{taskId}/live` that starts `npm run dev` in the sandbox workspace and returns the exposed URL. Add `GET /api/dev/{taskId}/live` to check status and `DELETE /api/dev/{taskId}/live` to stop.
  Files: `backend/app/routes/dev.py`

- [x] **4.2 Add "Run Live" button to dev-task detail** — For slides mode tasks, show a "Run Live" button that calls the live endpoint and displays the returned URL (as a link or iframe).
  Files: `frontend/src/app/(app)/development/[id]/page.tsx`
  Depends on: 4.1

### Group 5: Frontend — Slides UI

- [x] **5.1 Update slides create/edit form** — Add deck config fields (subtitle, icon, theme dropdown, appearance toggle, palette dropdown). Remove images upload section.
  Files: `frontend/src/app/(app)/slides/page.tsx`, `frontend/src/app/(app)/slides/[id]/page.tsx`

- [x] **5.2 Restrict attachment upload to PowerPoint** — Update file upload accept filter to `.pptx` only. Change label from "Attachments" to "PowerPoint Template".
  Files: `frontend/src/app/(app)/slides/[id]/page.tsx`

- [x] **5.3 Update API types** — Add deck config fields to Slides interface. Remove images. Update SlidesCreate/SlidesUpdate types.
  Files: `frontend/src/lib/api.ts`

### Group 6: Tests

- [x] **6.1 Update slides model tests** — Test deck config defaults, PowerPoint-only validation, images field removal.
  Files: `backend/tests/test_slides_service.py`

- [x] **6.2 Update dev-task pipeline tests** — Test single autopilot invocation, deck config parsing, PowerPoint porting conditional, screenshot export.
  Files: `backend/tests/test_dev_agent.py`
