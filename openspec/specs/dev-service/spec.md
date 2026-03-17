## MODIFIED Requirements

### Requirement: Dev task creation with two modes
The system SHALL support two dev task modes: **Mockup** and **OpenSpec**. Both modes SHALL execute via the GitHub Copilot CLI sandbox rather than in-process code generation.

#### Scenario: Create Mockup dev task
- **WHEN** a user creates a dev task with mode "mockup" linked to a spec
- **THEN** the system SHALL create a task that will execute the Mockup pipeline in the CLI sandbox using the spec's Mockup Description section

#### Scenario: Create OpenSpec dev task
- **WHEN** a user creates a dev task with mode "openspec" linked to a spec
- **THEN** the system SHALL create a task that will execute the OpenSpec pipeline in the CLI sandbox using the spec's OpenSpec Config section

### Requirement: Mockup pipeline execution
The system SHALL execute the Mockup pipeline by delegating to the CLI sandbox: initialize a project, run `openspec-propose` with the mockup description, and capture Playwright screenshots on completion.

#### Scenario: Mockup pipeline stages
- **WHEN** a Mockup dev task is triggered
- **THEN** the sandbox SHALL execute: (1) `openspec init` to scaffold a new project, (2) `openspec-propose` with the Mockup Description as the prompt, (3) apply the proposal, (4) start the dev server, (5) capture screenshots with Playwright

#### Scenario: Mockup pipeline completion
- **WHEN** the Mockup pipeline completes successfully
- **THEN** the dev task status SHALL be updated to "completed" with screenshots and a downloadable code archive attached

### Requirement: OpenSpec pipeline execution
The system SHALL execute the OpenSpec pipeline by delegating to the CLI sandbox: initialize a project, run foundation proposal, apply it, then run all feature proposals in parallel and apply each, finishing with Playwright screenshots.

#### Scenario: OpenSpec pipeline — foundation phase
- **WHEN** an OpenSpec dev task is triggered
- **THEN** the sandbox SHALL execute: (1) `openspec init`, (2) `openspec-propose` with the foundation prompt from the OpenSpec Config, (3) `openspec-apply` to implement the foundation

#### Scenario: OpenSpec pipeline — feature phase
- **WHEN** the foundation phase completes
- **THEN** the sandbox SHALL execute `openspec-propose` for each feature in parallel (using prompts from the OpenSpec Config), followed by `openspec-apply` for each

#### Scenario: OpenSpec pipeline — screenshot phase
- **WHEN** all features are applied
- **THEN** the sandbox SHALL start the dev server and capture Playwright screenshots of the complete application

### Requirement: Pipeline status tracking
The system SHALL track and expose the status of each pipeline stage so the frontend can show progress.

#### Scenario: Stage progress updates
- **WHEN** a pipeline is executing
- **THEN** each stage (init, propose, apply, screenshots) SHALL report its status (pending, running, completed, failed) via the task status API

#### Scenario: Parallel feature tracking
- **WHEN** OpenSpec mode executes features in parallel
- **THEN** each feature's propose/apply stages SHALL be tracked independently with individual status updates

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
- **WHEN** a new feature iteration is appended to an OpenSpec dev task with a completed foundation
- **THEN** the sandbox SHALL execute only the new feature's `openspec-propose` + `openspec-apply` in the existing project workspace
- **AND** restart the dev server and capture Playwright screenshots
- **AND** the task status SHALL remain "running" during feature execution and update to "completed" only when all iterations (including the new one) are done

#### Scenario: Queued feature executes after foundation
- **WHEN** a feature iteration with status "queued" exists on a dev task
- **AND** the foundation iteration completes successfully
- **THEN** the pipeline SHALL automatically pick up the queued feature and execute its `openspec-propose` + `openspec-apply`

#### Scenario: Multiple queued features
- **WHEN** multiple feature iterations are queued while foundation is running
- **THEN** the pipeline SHALL execute all queued features in parallel (up to max 3 concurrent) after foundation completes

### Requirement: Dev task feature iteration extension
The dev-service SHALL support dynamically appending feature iterations to an in-progress OpenSpec dev task.

#### Scenario: Append feature iteration
- **WHEN** the spec agent calls the dev service to append a feature iteration
- **THEN** the dev service SHALL create a new iteration with the feature's `openspec-propose` instruction, status "queued" or "pending" (depending on foundation status), and link it to the dev task

#### Scenario: Append rejected for mockup mode
- **WHEN** a feature iteration append is requested for a Mockup mode dev task
- **THEN** the dev service SHALL reject the request with an error indicating only OpenSpec mode supports incremental features

#### Scenario: Foundation completion triggers queued features
- **WHEN** the foundation iteration completes on a dev task that has queued feature iterations
- **THEN** the dev service SHALL transition all queued iterations to "pending" and trigger pipeline execution for them
