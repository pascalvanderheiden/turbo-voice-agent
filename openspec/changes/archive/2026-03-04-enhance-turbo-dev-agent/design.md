## Context
The Turbo Dev Agent currently calls `AsyncOpenAI` directly for code generation. The GitHub Copilot SDK provides a production-grade agent runtime with BYOK support that handles planning, tool invocation, and file operations natively. The current single-pass pipeline doesn't leverage the spec hierarchy (foundation → features).

## Goals / Non-Goals
- **Goals**:
  - Use Copilot SDK Python client with BYOK for Azure AI Foundry
  - Support two pipeline modes: mock (quick) and sequence (iterative)
  - Show plan output per iteration in the UI
  - Link specs ↔ dev tasks bidirectionally
  - Browse/install skills from skills.sh on the agents page
- **Non-Goals**:
  - Full CI/CD deployment pipeline
  - Multi-user collaboration on dev tasks
  - Running skills server-side (skills are informational/config for now)

## Decisions

### Decision: Copilot SDK BYOK over raw OpenAI
The `github-copilot-sdk` Python package provides `CopilotClient` with BYOK provider config. For Azure AI Foundry with gpt-5.3-codex, use `type: "openai"`, `base_url: "https://{host}/openai/v1/"`, `wire_api: "responses"`. This replaces the current manual `AsyncOpenAI` setup.

**Alternatives**: Keep raw OpenAI SDK (simpler, but doesn't benefit from Copilot's agent runtime for tool orchestration).

### Decision: Dual Pipeline with Iteration Model
- **Mock mode**: Single iteration, takes full spec content (foundation + features concatenated), generates one GUI-only application
- **Sequence mode**: N iterations — iteration 0 = foundation, iterations 1..N = features. Each iteration has its own Plan → Build → Run → Test stages. Features are added incrementally to the same workspace.

The `DevTask` model gains:
- `mode: "mock" | "sequence"` field
- `iterations: list[DevIteration]` — each with stages[], output, and a reference to the spec part being developed
- `current_iteration: int` tracking progress

### Decision: Skills as Browseable Catalog
Skills from skills.sh are presented as a searchable catalog on the Agents page. Users can see what skills are available. The skills.sh leaderboard data is fetched client-side by scraping the page (no API available). Installed skills are shown separately.

### Decision: OpenSpec as Iteration Driver
In sequence mode, the pipeline reads the spec's foundation and features from the spec service. Each feature becomes an iteration. The plan for each iteration is aware of what was built in previous iterations, enabling cumulative development.

## Risks / Trade-offs
- **Copilot SDK dependency**: Adds `github-copilot-sdk` package; requires Copilot CLI installed OR BYOK-only mode
- **Sequence mode complexity**: Multiple iterations increase pipeline run time significantly
- **skills.sh scraping**: No official API; catalog display may break if site structure changes

## Open Questions
- Should sequence mode allow partial re-runs (retry a single feature iteration)?
- Should the mock mode also support iterative refinement?
