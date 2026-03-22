## MODIFIED Requirements

### Requirement: Dev task creation with two modes
The system SHALL support two dev task modes: **Mockup** and **Sequential** (renamed from OpenSpec). Both modes SHALL execute via the GitHub Copilot CLI sandbox using direct `copilot --autopilot` invocations rather than openspec CLI tooling.

#### Scenario: Create Mockup dev task
- **WHEN** a user creates a dev task with mode "mockup" linked to a spec
- **THEN** the system SHALL create a task that will execute the Mockup pipeline in the CLI sandbox using the spec's Mockup Description section

#### Scenario: Create Sequential dev task
- **WHEN** a user creates a dev task with mode "sequential" linked to a spec
- **THEN** the system SHALL create a task that will execute the Sequential pipeline in the CLI sandbox using the spec's foundation and feature descriptions

#### Scenario: Backward compatibility with openspec mode
- **WHEN** a dev task exists with mode "openspec" in the database
- **THEN** the system SHALL treat it identically to mode "sequential"

### Requirement: Mockup pipeline execution
The system SHALL execute the Mockup pipeline with 4 stages: `init`, `skills`, `implement`, `screenshots`. The implement stage uses a single Copilot CLI invocation with `--autopilot --yolo --experimental --agent squad` flags.

#### Scenario: Mockup pipeline stages
- **WHEN** a Mockup dev task is triggered
- **THEN** the sandbox SHALL execute: (1) `init` — squad install and `squad init`, (2) `skills` — install marketplace + local skills, (3) `implement` — run `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<mockup description>"`, (4) `screenshots` — start dev server and capture with Playwright

#### Scenario: Mockup pipeline completion
- **WHEN** the Mockup pipeline completes successfully
- **THEN** the dev task status SHALL be updated to "completed" with screenshots and a downloadable code archive attached

### Requirement: Sequential pipeline execution
The system SHALL execute the Sequential pipeline with dynamic stages: `init`, `skills`, `implement-foundation`, `implement-feature-1`, …, `implement-feature-N`, `screenshots`. Each implement stage uses the same Copilot CLI command, with `--continue` for feature stages.

#### Scenario: Sequential pipeline — foundation implementation
- **WHEN** a Sequential dev task is triggered
- **THEN** the sandbox SHALL execute: (1) `init` — squad install and `squad init`, (2) `skills` — install skills, (3) `implement-foundation` — run `copilot --autopilot --yolo --experimental --model <model> --agent squad -p "<foundation description>"`

#### Scenario: Sequential pipeline — feature implementation
- **WHEN** the foundation implementation completes
- **THEN** for each feature N the sandbox SHALL run `copilot --autopilot --yolo --experimental --model <model> --agent squad --continue -p "<feature N description>"` as stage `implement-feature-N` in the same workspace

#### Scenario: Sequential pipeline — screenshot phase
- **WHEN** all feature implementations are complete
- **THEN** the sandbox SHALL start the dev server and capture Playwright screenshots of the complete application

### Requirement: Pipeline status tracking
The system SHALL track and expose the status of each pipeline stage so the frontend can show progress.

#### Scenario: Stage progress updates
- **WHEN** a pipeline is executing
- **THEN** each stage (init, skills, implement, screenshots) SHALL report its status (pending, running, completed, failed) via the task status API

#### Scenario: Sequential feature tracking
- **WHEN** Sequential mode executes features
- **THEN** each feature's implement stage SHALL be tracked independently with individual status updates

### Requirement: Model selection for CLI sandbox
The system SHALL allow users to configure the default GitHub Copilot CLI model used in the sandbox, and pass this model to all CLI commands.

#### Scenario: Model passed to CLI commands
- **WHEN** a dev task is executed in the sandbox
- **THEN** all Copilot CLI commands SHALL include the `--model` flag set to the user's selected model from their profile configuration

#### Scenario: Default model fallback
- **WHEN** no model is configured by the user
- **THEN** the system SHALL use a sensible default model (e.g., `claude-sonnet-4`)

### Requirement: Development Pipeline Execution
The dev-service SHALL execute pipeline stages as background tasks. The service SHALL support both full pipeline execution (foundation + all features) and **incremental feature pipeline execution** (single feature added after foundation).

#### Scenario: Incremental feature pipeline execution
- **WHEN** a new feature iteration is appended to a Sequential dev task with a completed foundation
- **THEN** the sandbox SHALL execute `copilot --autopilot --yolo --experimental --model <model> --agent squad --continue -p "<feature description>"` in the existing project workspace
- **AND** restart the dev server and capture Playwright screenshots
- **AND** the task status SHALL remain "running" during feature execution and update to "completed" only when all iterations are done

#### Scenario: Queued feature executes after foundation
- **WHEN** a feature iteration with status "queued" exists on a dev task
- **AND** the foundation iteration completes successfully
- **THEN** the pipeline SHALL automatically pick up the queued feature and execute its implement stage with `--continue`

#### Scenario: Multiple queued features
- **WHEN** multiple feature iterations are queued while foundation is running
- **THEN** the pipeline SHALL execute all queued features sequentially (one at a time, each with `--continue`) after foundation completes

### Requirement: Dev task feature iteration extension
The dev-service SHALL support dynamically appending feature iterations to an in-progress Sequential dev task.

#### Scenario: Append feature iteration
- **WHEN** the spec agent calls the dev service to append a feature iteration
- **THEN** the dev service SHALL create a new iteration with the feature's implementation prompt, status "queued" or "pending" (depending on foundation status), and link it to the dev task

#### Scenario: Append rejected for mockup mode
- **WHEN** a feature iteration append is requested for a Mockup mode dev task
- **THEN** the dev service SHALL reject the request with an error indicating only Sequential mode supports incremental features

#### Scenario: Foundation completion triggers queued features
- **WHEN** the foundation iteration completes on a dev task that has queued feature iterations
- **THEN** the dev service SHALL transition all queued iterations to "pending" and trigger sequential pipeline execution for them

### Requirement: Dev-task mode selection
The system SHALL support three dev-task modes: "mockup" (single iteration), "sequential" (multi-iteration with foundation + features), and "slides" (3-stage deck generation). The pipeline routing SHALL select the appropriate pipeline based on the task's mode field.

#### Scenario: Route slides mode to slides pipeline
- **WHEN** a dev-task with mode "slides" starts execution
- **THEN** system calls _run_slides_pipeline() with the task's slides content and configuration

#### Scenario: Route sequential mode
- **WHEN** a dev-task with mode "sequential" (or legacy "openspec") starts execution
- **THEN** system routes to _run_sequential_pipeline()

#### Scenario: Route mockup mode
- **WHEN** a dev-task with mode "mockup" starts execution
- **THEN** system routes to _run_mockup_pipeline()

## REMOVED Requirements

### Requirement: OpenSpec status tracking on dev tasks
**Reason**: The openspec CLI is no longer used inside the sandbox. The `openspec_status` field (changeName, totalTasks, completedTasks, currentTask, filesChanged) and the `_poll_openspec_status()` method are removed.
**Migration**: Stage-level status tracking (pending/running/completed/failed per stage) provides sufficient progress visibility.

### Requirement: Dev-task archived field
**Reason**: Not changed — this requirement remains as-is in the main spec.
**Migration**: N/A

## RENAMED Requirements

- FROM: `OpenSpec pipeline execution` → TO: `Sequential pipeline execution`
- FROM: `Create OpenSpec dev task` → TO: `Create Sequential dev task`
