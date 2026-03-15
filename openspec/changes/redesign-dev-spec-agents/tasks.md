## 1. Infrastructure — Sandbox Container App

- [x] 1.1 Create Bicep module `infra/modules/container-app-sandbox.bicep` for the sandbox Container App with Docker-in-Docker support, internal-only ingress, min 1 / max 5 replicas, and managed identity
- [x] 1.2 Create Dockerfile for the sandbox image: base Docker-in-Docker, install GitHub Copilot CLI, Node.js, Playwright, and OpenSpec CLI
- [x] 1.3 Add `sandbox_state` Cosmos DB container (partition key `/userId`, 400 RU/s) to `infra/modules/cosmos-db.bicep`
- [x] 1.4 Wire sandbox module into `infra/main.bicep` with environment variables for backend ↔ sandbox communication
- [x] 1.5 Update `azure.yaml` to include sandbox service build and deploy steps
- [x] 1.6 Add sandbox Docker image build to ACR in CI/CD pipeline (`.github/workflows/deploy.yml`)

## 2. Backend — Sandbox Service

- [x] 2.1 Create `backend/app/models/sandbox.py` with `SandboxState`, `SandboxTask`, `SandboxConfig` models (status, skills hash, GitHub token ref, model selection)
- [x] 2.2 Create `backend/app/services/sandbox_service.py` with `SandboxService` class: `provision_sandbox()`, `destroy_sandbox()`, `health_check()`, `execute_command()`, `stream_output()`, `sync_skills()`, `get_state()`
- [x] 2.3 Create `backend/app/services/inmemory_sandbox_service.py` with `InMemorySandboxService` for local dev/testing fallback
- [x] 2.4 Add sandbox service initialization to `backend/app/main.py` lifespan with Cosmos DB and in-memory dual implementation
- [x] 2.5 Create `backend/app/routes/sandbox.py` with endpoints: `POST /sandbox/tasks`, `GET /sandbox/tasks/{id}/stream` (SSE), `GET /sandbox/status`, `POST /sandbox/recreate`
- [x] 2.6 Write tests for `SandboxService` — provisioning, skill sync, health checks, command execution

## 3. Backend — Sandbox Auth

- [x] 3.1 Add `github_sandbox_token` (encrypted) and `github_sandbox_connected_at` fields to `UserProfile` model
- [x] 3.2 Add `PUT /user/sandbox-token` and `DELETE /user/sandbox-token` endpoints to `backend/app/routes/user.py`
- [x] 3.3 Implement token encryption at rest using a service-level encryption key (env var `SANDBOX_TOKEN_KEY`)
- [x] 3.4 Add token injection logic to `SandboxService.provision_sandbox()` — call `gh auth login --with-token` in sandbox
- [x] 3.5 Write tests for token storage, retrieval, deletion, and injection into sandbox

## 4. Backend — Spec Agent Redesign

- [x] 4.1 Update `backend/app/agents/spec_agent.py` generation prompts to produce two-part format: Mockup Description + OpenSpec Config
- [x] 4.2 Update foundation generation system prompt to output `## Mockup Description` section (~200 words, layout, components, interactions, visual identity)
- [x] 4.3 Update feature generation to produce `## OpenSpec Config` section with `### Foundation` (one `openspec-propose` prompt) and `### Features` (one `openspec-propose` prompt per feature)
- [x] 4.4 Update `optimize_spec` to preserve two-part format structure during optimization
- [x] 4.5 Update `Spec` model if needed to track the new format version
- [x] 4.6 Write tests for spec generation — verify two-part output format, mockup description word count, OpenSpec Config structure

## 5. Backend — Dev Agent Redesign

- [x] 5.1 Refactor `backend/app/agents/dev_agent.py` — rename modes from mock/sequence to mockup/openspec, remove in-process code generation pipeline
- [x] 5.2 Implement Mockup pipeline: parse spec's Mockup Description → delegate to sandbox (`openspec init` → `openspec-propose` with description → apply → start dev server → Playwright screenshots)
- [x] 5.3 Implement OpenSpec pipeline: parse spec's OpenSpec Config → delegate to sandbox (`openspec init` → foundation propose → apply → parallel feature proposes → apply each → dev server → screenshots)
- [x] 5.4 Add parallel feature execution logic with max 3 concurrent sandbox commands
- [x] 5.5 Implement stage-level status tracking (init, propose, apply, screenshots) with updates pushed via sandbox SSE
- [x] 5.6 Implement code artifact packaging — zip workspace from sandbox, store temporarily for download
- [x] 5.7 Add model selection passthrough — read user's configured model from profile, pass `--model` flag to all CLI commands
- [x] 5.8 Update `DevTask` model: rename modes, add `screenshots[]`, `artifact_url`, `sandbox_task_id` fields
- [x] 5.9 Write tests for Mockup pipeline, OpenSpec pipeline, parallel feature execution, and model passthrough

## 6. Frontend — Agent Page Sandbox Config

- [x] 6.1 Add Sandbox Config section to `frontend/src/app/(app)/agents/page.tsx` with sandbox status indicator, model selector dropdown, and link to GitHub auth settings
- [x] 6.2 Create `frontend/src/components/agents/sandbox-config.tsx` component with model selection (persist via `PUT /user/profile`), sandbox status display, and recreate button
- [x] 6.3 Add sandbox-related API functions to `frontend/src/lib/api.ts`: `sandboxApi.status()`, `sandboxApi.recreate()`, `sandboxApi.streamTask()`
- [x] 6.4 Add model list to API or hardcode initial set (claude-sonnet-4, gpt-4.1, etc.) with user's selection highlighted

## 7. Frontend — Profile Settings Auth

- [x] 7.1 Create or extend profile settings page at `frontend/src/app/(app)/settings/page.tsx` with GitHub Copilot Sandbox connection section
- [x] 7.2 Create `frontend/src/components/settings/sandbox-auth.tsx` component with connect/disconnect flow, status display, following the To-Do OAuth pattern
- [x] 7.3 Add API functions: `userApi.setSandboxToken()`, `userApi.deleteSandboxToken()`, `userApi.getSandboxStatus()`

## 8. Frontend — Dev Task UI Updates

- [x] 8.1 Update dev task creation UI to show "Mockup" and "OpenSpec" mode options (replace "Mock" and "Sequence")
- [x] 8.2 Create `frontend/src/components/dev/cli-terminal-viewer.tsx` — real-time terminal-style viewer consuming SSE stream from `/sandbox/tasks/{id}/stream`
- [x] 8.3 Create `frontend/src/components/dev/screenshot-gallery.tsx` — thumbnail grid with full-size lightbox viewer for captured screenshots
- [x] 8.4 Add "Download Code" button to dev task detail view, calling artifact download endpoint
- [x] 8.5 Update dev task detail view to integrate terminal viewer (during execution), screenshot gallery (on completion), and download button
- [x] 8.6 Add stage progress indicators showing current pipeline stage (init → propose → apply → screenshots)

## 9. Integration & Testing

- [x] 9.1 End-to-end test: generate spec → create Mockup dev task → verify sandbox execution → verify screenshots and download
- [x] 9.2 End-to-end test: generate spec → create OpenSpec dev task → verify foundation + parallel features → verify screenshots and download
- [x] 9.3 Test skill sync: install skill → verify sandbox recreation → verify skill present in sandbox
- [x] 9.4 Test auth flow: connect token in settings → trigger dev task → verify CLI authenticates successfully
- [x] 9.5 Test live streaming: trigger task → verify SSE stream delivers real-time CLI output to frontend
- [x] 9.6 Add `USE_CLI_SANDBOX` feature flag to backend env — when false, fall back to existing in-process pipeline for rollback safety
