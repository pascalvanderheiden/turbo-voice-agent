## Context

The dev pipeline currently runs 5 stages (init → propose → apply → archive → screenshots) in a sandbox container. Each stage executes Copilot CLI commands sequentially. The sandbox has Node.js, Git, OpenSpec CLI, and Copilot CLI pre-installed. Skills are installed during the init stage, and openspec initialization also happens during init. There is no concept of multi-agent collaboration — a single Copilot CLI session handles everything.

Squad-PR (`@bradygaster/squad-cli`) is a multi-agent runtime for GitHub Copilot that creates a team of specialist agents in a `.squad/` directory. Each agent has a charter, role, and accumulated history. The squad coordinates work through a routing system and logs decisions. It's installed via npm and operated via CLI commands (`squad init`, `squad hire`, `squad shell`).

## Goals / Non-Goals

**Goals:**
- Install squad-cli in the sandbox container alongside existing tools
- Break out the init stage into dedicated openspec, skills, and squad stages for better visibility
- Initialize a squad per dev task, with team composition derived from the foundation spec
- Visualize the squad team in the dev-task detail UI so users see who's working on their spec
- Stream squad agent activity through the existing pipeline output mechanism

**Non-Goals:**
- Replacing the existing Copilot CLI — squad orchestrates on top of it
- VS Code integration — sandbox is TUI-only, so only CLI commands are used
- Persistent squads across dev tasks — each task gets a fresh squad
- Implementing the squad SDK programmatically — CLI-only approach

## Decisions

### 1. Squad installation: Global npm install in Dockerfile

Install `@bradygaster/squad-cli` globally in the sandbox Dockerfile. This avoids installing it at pipeline time (slow) and ensures it's always available.

**Alternative considered:** Install at pipeline time via `npm install -g`. Rejected because it adds 10-15s to every dev task and requires network access.

### 2. Pipeline stages: 8-stage sequence

New stage order: `init → openspec → skills → squad → propose → apply → archive → screenshots`

- **init**: Git init, workspace setup (unchanged)
- **openspec**: Run `openspec init --tools github-copilot --force` (moved from entrypoint.sh to explicit stage)
- **skills**: Install marketplace skills via npx + sync local skills from blob (moved from init, gives visibility)
- **squad**: Run `squad init`, generate team.md/routing.md/directives.md from spec, run `squad hire` per agent
- **propose/apply/archive/screenshots**: Existing stages, but propose/apply can optionally route through squad shell

**Alternative considered:** Keep 5 stages, run squad setup silently in init. Rejected because the user specifically wants visibility into each setup step.

### 3. Team generation from foundation spec

Parse the foundation spec content to derive:
- **Team roles**: Extract tech stack mentions (React → Frontend Dev, Python/FastAPI → Backend Dev, etc.)
- **Routing rules**: Map spec sections to agent roles
- **Directives**: Extract coding conventions and constraints from spec

Generate `.squad/team.md`, `.squad/routing.md`, and `.squad/directives.md` files programmatically, then run `squad hire --name <name> --role <role>` for each agent.

Default team composition (always present):
- **Lead** — Scope, architecture decisions, code review
- **Scribe** — Memory, decisions, session logs (silent)

Dynamic roles (added based on spec analysis):
- Frontend Dev (if React/Next.js/UI mentioned)
- Backend Dev (if API/Python/FastAPI mentioned)
- Tester (if testing requirements present)
- DevOps (if infrastructure/deployment mentioned)

### 4. Squad metadata on DevTask model

Add a `squad` field to DevTask containing:
- `teamMembers`: Array of `{ name, role, expertise, status }` — populated during squad stage
- `decisions`: Array from `.squad/decisions.md` — updated during propose/apply
- `activity`: Array of recent agent actions — streamed during execution

This data is persisted in Cosmos DB and returned via the API for the frontend to render.

### 5. Frontend squad visualization

Add a "Squad" card/panel in the dev-task detail page showing:
- Team roster with agent names, roles, and status indicators (idle/working/done)
- Live activity feed showing which agent is doing what
- Decisions log showing architectural choices made by the squad

Use the existing Turbo Agent design language (dark cards, brand colors, Tabler icons).

### 6. Squad CLI interaction via sandbox exec

All squad commands run through `_sandbox_exec()` in dev_agent.py, same as other CLI tools. The squad shell is NOT used interactively — instead, individual squad commands are executed:
- `squad init` — initialize .squad/ directory
- `squad hire --name X --role Y` — add team members
- `squad status` — check team status (for streaming to frontend)

For propose/apply, we continue using Copilot CLI (with `--continue`) since squad enhances the agent context via `.squad/` files that Copilot reads automatically.

## Risks / Trade-offs

- **[Squad CLI version stability]** → Pin to a specific version in Dockerfile, test before upgrading
- **[Increased sandbox image size]** → squad-cli is a lightweight npm package (~5MB), minimal impact
- **[Team generation accuracy]** → Default team is always reasonable; spec-derived roles are best-effort. Users see what was generated and can iterate.
- **[Stage count increase]** → 8 stages means more UI elements. Mitigated by the stages being fast (openspec/skills/squad are each <30s)

## Open Questions

- Should squad decisions be surfaced as a separate tab or inline with the pipeline output?
- Should users be able to customize team composition before the squad stage runs?
