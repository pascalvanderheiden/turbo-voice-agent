## MODIFIED Requirements

### Requirement: Development Pipeline Execution
The system SHALL support two pipeline modes: **mock** and **sequence**. Each mode executes as a background task with stage-by-stage status updates.

#### Scenario: Mock mode pipeline
- **WHEN** a pipeline is triggered with mode "mock"
- **THEN** the system SHALL create a single iteration containing all four stages (Plan → Build → Run → Test)
- **AND** the Plan stage SHALL receive the complete spec content (foundation + all features concatenated)
- **AND** the Build stage SHALL generate a GUI-only mock application representing the end-state vision
- **AND** the system SHALL use the GitHub Copilot SDK with BYOK provider config for code generation

#### Scenario: Sequence mode pipeline
- **WHEN** a pipeline is triggered with mode "sequence"
- **THEN** the system SHALL create N iterations: iteration 0 for the foundation spec, iterations 1..N for each feature spec
- **AND** each iteration SHALL have its own Plan → Build → Run → Test stages
- **AND** the Plan stage for each iteration SHALL include context from all previously completed iterations
- **AND** the Build stage for the foundation iteration SHALL generate the base application
- **AND** the Build stage for feature iterations SHALL add functionality to the existing workspace from the previous iteration

#### Scenario: Plan stage output
- **WHEN** the Plan stage completes for any iteration
- **THEN** the plan output SHALL be stored as structured content (not just raw text)
- **AND** the plan SHALL reference the spec part (foundation or feature) being developed

#### Scenario: Pipeline failure in sequence mode
- **WHEN** an iteration fails in sequence mode
- **THEN** the pipeline SHALL stop at that iteration
- **AND** previous completed iterations SHALL remain intact
- **AND** the task status SHALL be set to "failed" with the current iteration index recorded

### Requirement: Development Task Storage
The system SHALL store development tasks with title, specId, status, mode, iterations, artifacts, and timestamps. The mode field determines whether the task follows the mock or sequence pipeline path.

#### Scenario: Create development task with mode
- **WHEN** a user creates a dev task with a title, optional specId, and mode ("mock" or "sequence")
- **THEN** the system SHALL create a task with the specified mode defaulting to "mock"
- **AND** if mode is "sequence" and a specId is provided, the system SHALL pre-populate iterations from the spec's foundation and features

#### Scenario: Create development task from spec
- **WHEN** a user triggers a dev task from an existing spec
- **THEN** the system SHALL create a task linked to the spec via specId
- **AND** the task title SHALL default to the spec title if not provided
- **AND** the spec SHALL be marked with a reference to the dev task for bidirectional linking

## ADDED Requirements

### Requirement: Copilot SDK BYOK Integration
The Turbo Dev Agent SHALL use the GitHub Copilot SDK Python client (`github-copilot-sdk`) with BYOK provider configuration for code generation instead of raw OpenAI SDK calls.

#### Scenario: Copilot SDK session creation
- **WHEN** the dev agent needs to generate code
- **THEN** it SHALL create a `CopilotClient` session with BYOK provider config: `type: "openai"`, `base_url` pointing to Azure AI Foundry's `/openai/v1/` endpoint, `wire_api: "responses"`, and the API key from environment
- **AND** the model SHALL be configurable via `DEV_CODEX_DEPLOYMENT` env var (default: "gpt-5.3-codex")

#### Scenario: Fallback to raw API
- **WHEN** the Copilot SDK is not installed or fails to initialize
- **THEN** the system SHALL fall back to direct `AsyncOpenAI` Responses API calls (current behavior)

### Requirement: Spec ↔ Dev Task Bidirectional Linking
When a development task is created from a spec, both entities SHALL reference each other.

#### Scenario: Spec links to dev task
- **WHEN** a dev task is created with a specId
- **THEN** the spec SHALL be updated with a `devTaskId` field pointing to the new task
- **AND** the spec's status SHALL be set to "in-development"

#### Scenario: Dev task completion updates spec
- **WHEN** a dev task pipeline completes successfully
- **THEN** the linked spec's status SHALL be updated to "developed"

#### Scenario: Get dev task from spec
- **WHEN** `GET /api/specs/{id}/dev-task` is called for a spec with a linked dev task
- **THEN** the system SHALL return the linked dev task summary

### Requirement: Development Iteration Model
Each development task SHALL contain one or more iterations, each representing a discrete development unit.

#### Scenario: Iteration structure
- **WHEN** a task is created
- **THEN** each iteration SHALL have: `iterationIndex`, `label` (e.g., "Foundation: Dark Cyberpunk" or "Feature: Combat System"), `specPartId` (the ID of the foundation or feature spec), and its own `stages[]` array

#### Scenario: Iteration progress tracking
- **WHEN** a sequence pipeline is running
- **THEN** the task SHALL track `currentIteration` indicating which iteration is actively executing
- **AND** completed iterations SHALL have all stages marked as "completed"

### Requirement: Agent Skills Configuration
The Turbo Dev Agent SHALL support configurable skills that provide domain-specific knowledge for code generation.

#### Scenario: Skills from local directory
- **WHEN** the dev agent initializes
- **THEN** it SHALL scan `.agents/skills/` for installed skill definitions
- **AND** include relevant skill instructions as context in code generation prompts

#### Scenario: List installed skills
- **WHEN** `GET /api/agents/skills` is called
- **THEN** the system SHALL return a list of installed skills with name, description, and source
