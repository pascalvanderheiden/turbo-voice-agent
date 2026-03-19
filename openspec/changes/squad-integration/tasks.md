## 1. Sandbox: Install Squad CLI

- [ ] 1.1 Add `RUN npm install -g @bradygaster/squad-cli` to `sandbox/Dockerfile` after existing global npm installs
- [ ] 1.2 Verify `squad --version` runs successfully in a fresh container build

## 2. Backend: Update Pipeline Stages

- [ ] 2.1 Update `STAGE_NAMES` in `backend/app/services/dev_service.py` to: `["init", "openspec", "skills", "squad", "propose", "apply", "archive", "screenshots"]`
- [ ] 2.2 Add `squad` field to DevTask model in `backend/app/models/dev_task.py` — optional dict with `teamMembers: list[dict]` (each member has name, role, expertise, status)
- [ ] 2.3 Update both Cosmos and InMemory dev services to persist/return the squad field

## 3. Backend: OpenSpec Stage Handler

- [ ] 3.1 In `dev_agent.py`, extract openspec init logic from the current init stage into a new `_run_openspec_stage()` method that runs `openspec init --tools github-copilot --force` via `_sandbox_exec`
- [ ] 3.2 Remove the openspec init from `entrypoint.sh` (it now runs as an explicit pipeline stage)

## 4. Backend: Skills Stage Handler

- [ ] 4.1 In `dev_agent.py`, extract skill installation logic from current init handling into a new `_run_skills_stage()` method that calls `_install_skills_in_sandbox()` and `_verify_skills_in_sandbox()`
- [ ] 4.2 Ensure the skills stage streams output through `_pipeline_outputs` with stage label "skills"

## 5. Backend: Squad Stage Handler

- [ ] 5.1 Create `_run_squad_stage()` method in `dev_agent.py` that runs `squad init` in the workspace via `_sandbox_exec`
- [ ] 5.2 Add `_generate_squad_team()` helper that parses foundation spec content for tech stack keywords (React, Next.js, Python, FastAPI, TypeScript, Docker, etc.) and returns a list of team members with name, role, and expertise
- [ ] 5.3 Generate `.squad/team.md` with roster, `.squad/routing.md` with work routing rules, and `.squad/directives.md` with coding conventions — write these files to the sandbox workspace via the sandbox API
- [ ] 5.4 Run `squad hire --name <name> --role <role>` for each team member via `_sandbox_exec`
- [ ] 5.5 Run `squad doctor` and log output (non-fatal if it fails)
- [ ] 5.6 Store the generated team roster in the dev task's `squad.teamMembers` field via the dev service
- [ ] 5.7 Stream all squad setup activity through `_pipeline_outputs` with stage label "squad"

## 6. Backend: Pipeline Orchestration Update

- [ ] 6.1 Update the main pipeline execution method to call stages in new order: init → openspec → skills → squad → propose → apply → archive → screenshots
- [ ] 6.2 Ensure each new stage updates the iteration stage status (pending → running → completed/failed) through the existing `_update_stage_status()` mechanism

## 7. Frontend: Stage Metadata Update

- [ ] 7.1 Update `STAGE_META` in `development/[id]/page.tsx` to include entries for `openspec` (IconFileCode, "OpenSpec", purple), `skills` (IconPuzzle, "Skills", cyan), `squad` (IconUsersGroup, "Squad", pink)
- [ ] 7.2 Import new Tabler icons: `IconPuzzle`, `IconUsersGroup`, `IconFileCode` (if not already imported)

## 8. Frontend: Squad Visualization Panel

- [ ] 8.1 Add `squad` field to the frontend DevTask type in `lib/api.ts` — `squad?: { teamMembers: Array<{ name: string; role: string; expertise: string; status: string }> }`
- [ ] 8.2 Create a `SquadPanel` component in `development/[id]/page.tsx` that renders team member cards with: emoji + name, role badge, expertise tags, and status indicator (pulsing cyan dot for working, gray for idle, green check for done)
- [ ] 8.3 Add the `SquadPanel` to the dev-task detail page layout, rendered after the pipeline stages section when `task.squad?.teamMembers` is non-empty
- [ ] 8.4 Style squad cards using Turbo Agent design language: dark cards with border, brand color accents, compact layout that fits 3-4 agents per row on desktop

## 9. Verification

- [ ] 9.1 Run `npm run build` in frontend to verify no TypeScript errors
- [ ] 9.2 Verify the Dockerfile builds successfully with squad-cli installed
- [ ] 9.3 Commit and push all changes
