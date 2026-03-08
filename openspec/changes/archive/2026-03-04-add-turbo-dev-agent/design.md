## Context
The Turbo Voice Agent platform already supports research as a background task (fire-and-forget with polling). The Turbo Dev agent follows the same pattern but with a 4-stage pipeline. It leverages the GitHub Copilot SDK for AI-powered code generation and Playwright MCP for automated browser testing/screenshots.

## Goals
- Enable spec-to-application pipeline: pick a spec, auto-generate a working frontend
- 4-stage pipeline: Plan → Build → Run → Test with per-stage status tracking
- Store artifacts: Playwright snapshots, compressed source code
- Manual task creation for ad-hoc development work
- Consistent UI with existing pages (research, specs)

## Non-Goals
- Backend application generation (frontend-only for v1)
- Deployment to Azure (local run only for v1)
- Multi-file editing UI / code editor in the app
- CI/CD pipeline integration

## Decisions

### Pipeline Architecture
- **Decision**: 4-stage sequential pipeline executed as a background async task
- **Why**: Matches the research background task pattern; each stage can report progress
- **Alternatives**: WebSocket streaming (too complex for v1), polling (proven pattern)

### GitHub Copilot SDK Integration
- **Decision**: Use `@github/copilot-sdk` for code generation via gpt-5.3-codex
- **Why**: Purpose-built for code generation tasks, deployed in user's Foundry instance
- **Alternatives**: Direct Azure OpenAI (less code-specialized), local models (less capable)

### Playwright MCP for Testing
- **Decision**: Attach Playwright MCP server to the dev agent for browser automation
- **Why**: Can take snapshots, verify the app runs, produce visual evidence of success
- **Alternatives**: Puppeteer (less integrated), manual screenshots (not automated)

### Artifact Storage
- **Decision**: Store screenshots as base64 in the task model, compressed code as .tar.gz on disk in `.data/dev/`
- **Why**: Screenshots are small enough for inline storage; code archives need file system
- **Alternatives**: All on disk (harder to serve), all inline (code too large)

### Agent Registration
- **Decision**: Register as 5th specialist agent under Supervisor, same pattern as Notes/Brainstorm/Research/Spec agents
- **Why**: Consistent with existing architecture; supervisor handles routing

## Risks / Trade-offs
- **Risk**: gpt-5.3-codex may produce code that doesn't build → Mitigation: Build stage detects errors, retries once, reports failure
- **Risk**: Playwright requires a running dev server → Mitigation: Run stage starts the server, Test stage connects to it
- **Risk**: Long-running pipeline (minutes) → Mitigation: Per-stage status updates, frontend polls and shows stage progress

## Open Questions
- Should the dev agent support iterative refinement (fix build errors automatically)?
- Maximum number of retry attempts per stage before marking failed?
