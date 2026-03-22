## MODIFIED Requirements

### Requirement: Four-stage mockup pipeline
The mockup development pipeline SHALL use 4 stages in this order: `init`, `skills`, `implement`, `screenshots`. The `STAGE_NAMES` constant SHALL be updated to reflect this sequence.

#### Scenario: New mockup dev task has 4 stages
- **WHEN** a new mockup dev task is created
- **THEN** its iteration contains stages named init, skills, implement, screenshots — all with status "pending"

### Requirement: Dynamic sequential pipeline stages
The sequential development pipeline SHALL use dynamic stages: `init`, `skills`, `implement-foundation`, `implement-feature-1`, …, `implement-feature-N`, `screenshots`. Stage names are generated based on the number of features.

#### Scenario: Sequential dev task with 3 features
- **WHEN** a new sequential dev task is created with foundation + 3 features
- **THEN** its stages are: init, skills, implement-foundation, implement-feature-1, implement-feature-2, implement-feature-3, screenshots

#### Scenario: Single feature added later
- **WHEN** a feature is appended to a running sequential dev task
- **THEN** a new `implement-feature-N` stage is dynamically added before screenshots

### Requirement: Init stage
The `init` stage SHALL run `squad init` to initialize squad-pr in the workspace. This stage does NOT install or initialize the openspec CLI.

#### Scenario: Init stage executes
- **WHEN** the init stage executes
- **THEN** squad is initialized in the workspace via `squad init`, team members are hired, and `squad doctor` validates the configuration

### Requirement: Skills stage
The `skills` stage SHALL install all activated marketplace skills via their npx commands and sync local skills from blob storage.

#### Scenario: Marketplace and local skills installed
- **WHEN** the skills stage executes with 3 marketplace skills and 2 local skills activated
- **THEN** marketplace skills are installed via npx, local skills are skipped (pre-synced), and the stage output shows "Activated 5 skills in workspace"

#### Scenario: No skills activated
- **WHEN** the skills stage executes with no skills activated
- **THEN** the stage completes immediately with output "No skills to install"

### Requirement: Implement stage
The `implement` stage (mockup) or `implement-foundation` / `implement-feature-N` stages (sequential) SHALL run the Copilot CLI with `--autopilot --yolo --experimental --model <model> --agent squad -p "<prompt>"`. Feature stages SHALL additionally include the `--continue` flag.

#### Scenario: Mockup implement stage
- **WHEN** the implement stage executes for a mockup task
- **THEN** the sandbox runs `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<mockup description>"`

#### Scenario: Sequential foundation implement stage
- **WHEN** the implement-foundation stage executes
- **THEN** the sandbox runs `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<foundation description>"`

#### Scenario: Sequential feature implement stage
- **WHEN** an implement-feature-N stage executes
- **THEN** the sandbox runs `copilot --autopilot --yolo --experimental --model <model> --agent squad --continue -p "<feature description>"`

### Requirement: Stage ordering enforcement
Stages SHALL execute in strict order. A stage SHALL NOT start until the previous stage has completed successfully.

#### Scenario: Implement waits for skills
- **WHEN** the skills stage is still running
- **THEN** the implement stage remains in "pending" status

#### Scenario: Pipeline fails gracefully
- **WHEN** any stage fails (except squad doctor warnings)
- **THEN** subsequent stages are NOT executed and the dev task status is set to "failed"

### Requirement: Pipeline output streaming for all stages
All stages SHALL stream their stdout/stderr through the existing `_pipeline_outputs` mechanism so the frontend receives real-time updates via SSE.

#### Scenario: Implement stage streams output
- **WHEN** the implement stage is running
- **THEN** the Copilot CLI output appears in the pipeline stream with the appropriate stage label

## REMOVED Requirements

### Requirement: Eight-stage pipeline
**Reason**: Replaced by the simplified 4-stage mockup pipeline and dynamic sequential pipeline. The `openspec`, `squad`, `propose`, `apply`, and `archive` stages are removed.
**Migration**: Existing tasks with 8 stages will display their historical data but new tasks use the simplified stages.

### Requirement: OpenSpec stage
**Reason**: The openspec CLI is no longer installed or initialized in the sandbox. Project scaffolding is handled directly by the Copilot CLI `--autopilot` flag.
**Migration**: No replacement needed — the Copilot CLI handles project creation autonomously.

### Requirement: Squad stage
**Reason**: Squad initialization is now part of the `init` stage rather than a separate stage.
**Migration**: Squad init logic moves into the init stage handler.
