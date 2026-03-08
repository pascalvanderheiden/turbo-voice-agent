## Context
The agents page currently shows a static list of installed skills with no management capabilities. The skills.sh marketplace fetch fails with CORS, marketplace links are placeholder URLs that don't resolve, and there is no way to install or remove skills. The Turbo Dev Agent ignores installed skills entirely during code generation.

The `npx skills` CLI is the package manager for the open agent skills ecosystem. Key commands:
- `npx skills find [query]` — search for skills
- `npx skills add <owner/repo> --skill <name>` — install a skill from GitHub
- `npx skills add <owner/repo> --skill <name> -g -y` — install globally, skip prompts
- `npx skills check` — check for updates
- Skills are installed into `.agents/skills/<name>/` with `SKILL.md` + `references/` structure

## Goals / Non-Goals
- **Goals**:
  - Manage skills from the agents page UI (install, delete, search)
  - Install marketplace skills via `npx skills add` executed in background
  - Install local skills by copying a directory into `.agents/skills/`
  - Delete installed skills (remove directory)
  - Search skills.sh marketplace via backend proxy (avoid CORS)
  - Notify users of skill operations via existing notification system
  - Dev Agent selects and injects relevant skill content per project/spec
  - Per-project skill selection when creating dev tasks
  - Skills Agent as a specialist agent in the supervisor routing
- **Non-Goals**:
  - Building a custom skills package manager (use `npx skills`)
  - Running skills as server-side executors (skills are knowledge/context only)
  - Skill versioning or update management in v1

## Decisions

### Decision: Skills Agent as Specialist Agent
Create a `SkillsAgent` registered in the supervisor graph, handling: `install_skill`, `uninstall_skill`, `search_skills`, `list_skills`. This enables voice and chat users to manage skills via natural language ("install the react-native-expo skill"). The agent delegates to a `SkillsService` for actual operations.

**Alternatives**: Expose REST-only endpoints without agent integration (simpler, but no voice/chat support for skill management).

### Decision: Backend Proxy for skills.sh Search
Add `GET /api/agents/skills/search?q=<query>` that runs `npx skills find <query>` server-side and parses the output. This avoids CORS issues with direct client-side fetching from skills.sh.

**Alternatives**: Client-side scraping (broken by CORS), hardcoded catalog (stale quickly).

### Decision: `npx skills add` for Marketplace Install
Execute `npx skills add <owner/repo> --skill <name> -y` as a background subprocess on the backend. Return immediately with a "installing" status, push notification when complete.

**Alternatives**: Direct git clone + file copy (loses skills CLI validation and metadata). Using Copilot SDK to run commands (possible but overkill for simple shell commands; reserve for future if agent needs dynamic decision-making during install).

### Decision: Per-Project Skill Injection in Dev Agent
When building a dev task, the user selects which installed skills are relevant (or the agent auto-suggests based on spec keywords). The Dev Agent reads the selected skills' `SKILL.md` and key reference files, then appends condensed skill context to code generation prompts. Max ~2000 tokens of skill context per prompt to avoid overwhelming the model.

### Decision: File-Copy for Local Skill Install
`POST /api/agents/skills/install-local` accepts a `sourcePath` and `name`. The backend copies the directory into `.agents/skills/<name>/`. This supports users who have skill repos cloned locally.

## Risks / Trade-offs
- **npx skills CLI dependency**: Requires Node.js on the backend server, which is already available for the dev pipeline
- **Background process management**: Skill installs run as subprocesses; need timeout and cleanup
- **Skill context size**: Large skills (like carplay with 11 reference files) could consume significant prompt tokens; need truncation strategy
- **Security**: Running `npx skills add` executes code from GitHub repos; mitigated by the fact that skills are markdown/knowledge files, not executable code

## Open Questions
- Should auto-suggestion of skills use semantic matching (vector search on skill descriptions) or keyword matching?
- Should skill install status be persisted or is in-memory + notification sufficient?
