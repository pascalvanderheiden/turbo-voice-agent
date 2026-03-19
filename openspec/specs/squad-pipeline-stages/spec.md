## ADDED Requirements

### Requirement: Eight-stage pipeline
The development pipeline SHALL use 8 stages in this order: `init`, `openspec`, `skills`, `squad`, `propose`, `apply`, `archive`, `screenshots`. The `STAGE_NAMES` constant in `dev_service.py` SHALL be updated to reflect this sequence.

#### Scenario: New dev task has 8 stages
- **WHEN** a new dev task is created
- **THEN** its iterations contain stages named init, openspec, skills, squad, propose, apply, archive, screenshots — all with status "pending"

### Requirement: OpenSpec stage
The `openspec` stage SHALL run `openspec init --tools github-copilot --force` in the sandbox workspace. This replaces the openspec initialization currently done in `entrypoint.sh`.

#### Scenario: OpenSpec initialized in workspace
- **WHEN** the openspec stage executes
- **THEN** the workspace contains `.github/skills/` directory with openspec tooling and the stage completes with status "completed"

### Requirement: Skills stage
The `skills` stage SHALL install all activated marketplace skills via their npx commands and sync local skills from blob storage. This replaces the skill installation currently done during the init stage.

#### Scenario: Marketplace and local skills installed
- **WHEN** the skills stage executes with 3 marketplace skills and 2 local skills activated
- **THEN** marketplace skills are installed via npx, local skills are skipped (pre-synced), and the stage output shows "Activated 5 skills in workspace"

#### Scenario: No skills activated
- **WHEN** the skills stage executes with no skills activated
- **THEN** the stage completes immediately with output "No skills to install"

### Requirement: Squad stage
The `squad` stage SHALL initialize squad-pr in the workspace, generate team configuration from the spec, hire agents, and validate with `squad doctor`. See squad-sandbox-setup spec for details.

#### Scenario: Squad initialized for a foundation spec
- **WHEN** the squad stage runs for a dev task linked to a foundation spec about a Next.js + FastAPI app
- **THEN** a `.squad/` directory is created with team members matching the spec's tech stack

### Requirement: Stage ordering enforcement
Stages SHALL execute in strict order. A stage SHALL NOT start until the previous stage has completed successfully.

#### Scenario: Skills stage waits for openspec
- **WHEN** the openspec stage is still running
- **THEN** the skills stage remains in "pending" status

#### Scenario: Pipeline fails gracefully
- **WHEN** any stage fails (except squad doctor warnings)
- **THEN** subsequent stages are NOT executed and the dev task status is set to "failed"

### Requirement: Pipeline output streaming for new stages
All new stages (openspec, skills, squad) SHALL stream their stdout/stderr through the existing `_pipeline_outputs` mechanism so the frontend receives real-time updates via WebSocket.

#### Scenario: Squad stage streams agent hiring
- **WHEN** the squad stage hires 4 agents
- **THEN** each hire command's output appears in the pipeline stream with stage label "squad"
