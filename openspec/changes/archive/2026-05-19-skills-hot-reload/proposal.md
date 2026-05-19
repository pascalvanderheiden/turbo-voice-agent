## Why

Skills are currently re-synced from blob storage at the start of every dev-task pipeline (`_install_skills_in_sandbox`), adding latency and a redundant "skills" stage. When a user activates a skill via the marketplace, it's uploaded to blob storage but only becomes available in the sandbox at the next task — there's no immediate push. The sandbox should receive skills instantly on activation (hot reload) and dev-task pipelines should not need an install step at all.

## What Changes

- Add a `POST /skills/sync` endpoint to the sandbox server that re-syncs all skills from blob storage into `/home/agent/.copilot/skills/`
- Add a `POST /skills/push` endpoint to the sandbox server that accepts individual skill files directly (faster than full blob re-sync)
- Backend calls the sandbox push endpoint immediately after uploading a skill to blob storage on activation
- Backend calls the sandbox to delete a skill immediately on deactivation
- **BREAKING**: Remove the per-task `_install_skills_in_sandbox()` call and the "skills" pipeline stage from all dev-task modes (mockup, sequential, slides)
- Remove the `_verify_skills_in_sandbox()` Copilot CLI prompt (saves a premium request per task)
- Update `sandbox-skill-mount` spec requirements for hot-reload behavior

## Capabilities

### New Capabilities
- `skills-hot-reload`: Sandbox endpoints for receiving skill files on-demand and the backend integration to push skills immediately on activation/deactivation

### Modified Capabilities
- `sandbox-skill-mount`: Requirements change from "sync at container startup only" to "sync at startup + hot-reload on activation"
- `copilot-cli-sandbox`: Remove the "skills" pipeline stage from dev-task execution; skills are pre-loaded

## Impact

- `sandbox/server.js`: New `/skills/push` and `/skills/sync` endpoints
- `backend/app/main.py`: Activation/deactivation endpoints call sandbox after blob upload
- `backend/app/agents/dev_agent.py`: Remove `_install_skills_in_sandbox()`, `_verify_skills_in_sandbox()`, and all "skills" stage references from pipelines
- `backend/app/routes/dev.py`: Remove skills stage from iteration stage definitions
- Frontend: Remove "skills" stage from pipeline progress UI (if hardcoded)
