## Why

The development pipeline currently runs all work through a single Copilot CLI session per sandbox. There is no concept of specialized agents collaborating on different aspects of a spec. Squad-PR (https://bradygaster.github.io/squad-pr/) provides a multi-agent runtime for GitHub Copilot that lets us spin up a team of specialists — backend, frontend, testing, architecture — that fan out and work in parallel. Integrating Squad into the dev pipeline gives each spec a dedicated team, making development faster and more visible to the user.

Additionally, the pipeline stages are too coarse. We need new intermediate stages (openspec, skills, squad) to reflect the actual setup steps happening in the sandbox before code generation begins.

## What Changes

- Install `@bradygaster/squad-cli` globally in the sandbox Docker image
- Add three new pipeline stages between `init` and `propose`: **openspec** (init openspec in workspace), **skills** (install marketplace + local skills), **squad** (initialize squad from foundation spec, hire agents)
- Updated stage sequence: `init → openspec → skills → squad → propose → apply → archive → screenshots`
- For each dev task, generate a `.squad/` directory in the sandbox workspace based on the foundation spec content — team roles, routing rules, and directives derived from the spec's tech stack and capabilities
- Run `squad init` + `squad hire` in the sandbox to set up the team, then use the squad shell for propose/apply stages
- Add a visual "Squad" panel in the dev-task detail page showing team members, roles, and per-agent activity
- Stream squad agent activity back through the existing pipeline output WebSocket

## Capabilities

### New Capabilities
- `squad-sandbox-setup`: Installation and initialization of squad-pr CLI in the sandbox, including `squad init`, `squad hire`, and team configuration derived from spec content
- `squad-pipeline-stages`: New pipeline stages (openspec, skills, squad) and updated stage orchestration in the dev agent
- `squad-visualization`: Frontend UI component showing the squad team roster, agent roles, routing, and live activity indicators in the dev-task detail view

### Modified Capabilities

## Impact

- **sandbox/Dockerfile**: Add `npm install -g @bradygaster/squad-cli` to the image build
- **sandbox/entrypoint.sh**: No change needed (squad init happens at pipeline time, not container start)
- **backend/app/agents/dev_agent.py**: Major changes — new stage handlers for openspec, skills, squad; squad-aware propose/apply that delegates to squad shell
- **backend/app/services/dev_service.py**: Update `STAGE_NAMES` to include new stages
- **backend/app/models/dev_task.py**: Add squad metadata fields (team roster, agent activity)
- **frontend/src/app/(app)/development/[id]/page.tsx**: Add squad visualization panel, update `STAGE_META` with new stages
- **frontend/src/lib/api.ts**: Extend DevTask type with squad fields
