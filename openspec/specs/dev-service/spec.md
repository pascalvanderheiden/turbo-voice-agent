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
