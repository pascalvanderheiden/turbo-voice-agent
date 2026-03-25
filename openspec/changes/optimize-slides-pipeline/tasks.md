## 1. Update Stage Configuration

- [ ] 1.1 Change `SLIDES_STAGE_NAMES` in `backend/app/services/dev_service.py` from `["init", "skills", "slides"]` to `["init", "slides", "run"]`
- [ ] 1.2 Update any stage name references in `backend/app/services/dev_service.py` that depend on the old stage names

## 2. Rewrite Init Stage

- [ ] 2.1 Refactor the init stage in `_run_slides_pipeline()` to: clean workspace → run `create-deckio` with Slides entity config → verify `.github/` dir → init git → sync skills (move from separate stage)
- [ ] 2.2 Remove the standalone `skills` stage call from the pipeline — skills sync is now part of init

## 3. Rewrite Slides Stage

- [ ] 3.1 Replace the current `_sandbox_exec()` prompt-based Copilot invocation with `copilot --autopilot --yolo` running in the deck directory
- [ ] 3.2 Construct the slides prompt from the Slides entity `refined_draft` (extract `## Slides` section) with instructions to create slides using `.github` folder skills
- [ ] 3.3 Add PowerPoint handling: if a `.pptx` attachment exists on the Slides entity, include instructions in the prompt to use `deck-port-powerpoint` skill to import the PowerPoint content

## 4. Implement Run Stage

- [ ] 4.1 Add a new run stage handler that executes `npm install` in the deck directory
- [ ] 4.2 After install, start `npm run dev` as a long-running sandbox task in the deck directory
- [ ] 4.3 Add a health check loop that polls `/proxy/3333/` on the sandbox until the dev server responds (60s timeout)
- [ ] 4.4 Report the preview URL (`/api/dev/{task_id}/preview/`) in the pipeline output after the dev server is confirmed running

## 5. Fix Live Preview Routes

- [ ] 5.1 Simplify the `start_live` route in `backend/app/routes/dev.py` to return the proxy URL directly (dev server is already running from run stage)
- [ ] 5.2 Update the preview proxy route to return a clear error if the run stage hasn't completed yet

## 6. Update Frontend

- [ ] 6.1 Update the dev-task detail page to auto-show the preview iframe when the run stage completes, instead of requiring a "Run Live" button click
- [ ] 6.2 Update stage display names in the frontend pipeline visualization to show "init", "slides", "run"

## 7. Update Specs and Tests

- [ ] 7.1 Archive the existing `slides-pipeline` spec and replace with the updated version from this change
- [ ] 7.2 Archive the existing `slides-live-preview` spec and replace with the updated version
- [ ] 7.3 Add the new `slides-run-stage` spec to `openspec/specs/`
- [ ] 7.4 Update any existing tests that reference the old stage names (`skills` → removed, add `run`)
