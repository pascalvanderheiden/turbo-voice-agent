# Change: Enhance Turbo Dev Agent with Copilot SDK BYOK, Dual Pipelines, Skills Integration

## Why
The current Turbo Dev Agent uses raw `AsyncOpenAI` calls instead of the official GitHub Copilot SDK with BYOK. The pipeline only supports a single "generate everything at once" mode, limiting its usefulness for spec-driven development. Users need two distinct development paths: quick mock generation and iterative spec-driven development. Additionally, the agent should be extensible with skills from skills.sh, and dev tasks should be linked bidirectionally with specs.

## What Changes
- **Copilot SDK BYOK**: Refactor dev agent to use `github-copilot-sdk` Python SDK with BYOK provider config for Azure AI Foundry, using `wire_api: "responses"` for gpt-5.3-codex
- **Dual Pipeline Modes**:
  - **Mock Mode**: Takes the complete spec (foundation + all features) and generates a GUI-only mock application in one pass for quick visualization
  - **Sequence Mode**: Spec-driven iterative development — plans and builds the foundation first, then adds features one at a time in separate iterations. Each iteration has its own Plan step. Leverages OpenSpec structure (foundation → features)
- **Spec ↔ Dev Task Linking**: When a dev task is created from a spec, the spec is marked as "in development" and links bidirectionally to the task
- **Plan Output in App**: Plan stage output is rendered as structured content in the app (not just raw text), showing the implementation plan for each iteration
- **Skills Integration**: Add a skills marketplace section on the Agents page, allowing users to browse/search skills from skills.sh and view installed skills
- **MCP + Skills for Agent**: Enhance the dev agent with configurable skills alongside MCP servers

## Impact
- Affected specs: dev-service, agent-orchestration, web-app, mobile-app
- Affected code: `backend/app/agents/dev_agent.py`, `backend/app/models/dev_task.py`, `backend/app/services/dev_service.py`, `frontend/src/app/(app)/development/`, `frontend/src/app/(app)/agents/`, `mobile/app/dev-*`
- **BREAKING**: DevTask model gains `mode` field and `iterations` array; pipeline endpoint accepts mode parameter
