## 1. Backend — Copilot SDK Migration
- [x] 1.1 Install `github-copilot-sdk` Python package
- [x] 1.2 Refactor `DevAgent._call_codex()` to use `CopilotClient` with BYOK provider config (`type: "openai"`, `base_url`, `wire_api: "responses"`, `api_key`)
- [x] 1.3 Verify gpt-5.3-codex works through Copilot SDK BYOK with Azure AI Foundry endpoint
- [x] 1.4 Add skills config support — agent reads skill definitions from `.agents/skills/` and passes them as context

## 2. Backend — Dual Pipeline Modes
- [x] 2.1 Add `DevIteration` model: `iteration_index`, `label` (foundation/feature name), `spec_part_id`, `stages[]`, `workspace_path`
- [x] 2.2 Update `DevTask` model: add `mode` ("mock" | "sequence"), `iterations: list[DevIteration]`, `current_iteration: int`
- [x] 2.3 Update `DevTaskCreate` to accept `mode` field
- [x] 2.4 Implement mock pipeline: single iteration, full spec → single app generation (similar to current behavior)
- [x] 2.5 Implement sequence pipeline: fetch foundation spec + feature specs, create one iteration per part
- [x] 2.6 Sequence Plan stage: for each iteration, generate a plan that includes context from prior iterations
- [x] 2.7 Sequence Build stage: for foundation iteration, generate base app; for feature iterations, add to existing workspace
- [x] 2.8 Each iteration has independent Plan → Build → Run → Test stages
- [x] 2.9 Update trigger endpoint `POST /api/dev/{id}/trigger` to accept optional `mode` parameter

## 3. Backend — Spec ↔ Dev Task Linking
- [x] 3.1 When creating a dev task with `specId`, fetch the foundation spec and all child feature specs
- [x] 3.2 Add `devTaskId` field to Spec model for bidirectional linking
- [x] 3.3 Add `GET /api/specs/{id}/dev-task` endpoint to get linked dev task
- [x] 3.4 When pipeline starts, mark linked spec status as "in-development"
- [x] 3.5 When pipeline completes, update spec status to "developed"

## 4. Frontend — Development Pages Update
- [x] 4.1 Update dev task creation dialog: add mode selector (Mock / Sequence)
- [x] 4.2 Update dev detail page to show iterations with tabs/timeline
- [x] 4.3 Render Plan stage output as structured markdown (not raw text)
- [x] 4.4 In sequence mode, show progress across iterations (which feature is being built)
- [x] 4.5 Add "Develop" button on spec detail page that creates a linked dev task
- [x] 4.6 Show dev task link on spec cards when a spec is being developed

## 5. Frontend — Agents Page Skills Integration
- [x] 5.1 Add "Skills Marketplace" section to agents page
- [x] 5.2 Fetch skills catalog from skills.sh (client-side, with caching)
- [x] 5.3 Display skills as searchable card grid with name, description, install count
- [x] 5.4 Show installed skills (read from backend `/api/agents/skills` endpoint)
- [x] 5.5 Add backend endpoint `GET /api/agents/skills` to list installed skills from `.agents/skills/`
- [x] 5.6 Style skills section consistent with existing agents page design

## 6. Mobile — Development Updates
- [x] 6.1 Update dev task creation to include mode selector
- [x] 6.2 Update dev detail screen to show iterations
- [x] 6.3 Show plan output formatted in the plan step
- [x] 6.4 Add "Develop" action on spec detail screen

## 7. Validation
- [x] 7.1 Verify Copilot SDK BYOK connects to Azure AI Foundry with gpt-5.3-codex
- [x] 7.2 Test mock mode pipeline end-to-end
- [x] 7.3 Test sequence mode pipeline with a multi-feature spec
- [x] 7.4 Verify spec ↔ dev task bidirectional linking
- [x] 7.5 Verify skills section renders on agents page
- [x] 7.6 Run `npx expo export --platform ios` to verify mobile build
- [x] 7.7 Run `npm run build` to verify frontend build
