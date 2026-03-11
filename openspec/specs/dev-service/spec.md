# dev-service Specification

## Purpose
TBD - created by archiving change add-turbo-dev-agent. Update Purpose after archive.
## Requirements
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

### Requirement: Development Task CRUD Operations
The dev-service SHALL provide REST endpoints for creating, reading, listing, and deleting dev tasks. The `DELETE /api/dev/{id}` endpoint SHALL gracefully handle deletion of tasks in any status (pending, running, completed, failed) and SHALL clean up associated artifacts. Deletion errors SHALL be logged with the task ID and error details.

#### Scenario: Delete a running dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for a task with status "running"
- **THEN** the service SHALL cancel any in-progress pipeline stages
- **AND** remove the task record and associated artifacts
- **AND** return HTTP 200 with confirmation

#### Scenario: Delete a completed dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for a completed task
- **THEN** the service SHALL remove the task record and associated artifacts (screenshots, code archives)
- **AND** return HTTP 200 with confirmation

#### Scenario: Delete a non-existent dev task
- **WHEN** a user sends `DELETE /api/dev/{id}` for an ID that does not exist
- **THEN** the service SHALL return HTTP 404 with a descriptive error message

### Requirement: Development Pipeline Execution
The dev-service SHALL execute pipeline stages (Plan → Build → Run → Test) as background tasks immediately after a dev task is created. The service SHALL log each stage transition with structured JSON including taskId, stage name, status, duration, and any error details. The service SHALL ensure background task execution is reliable in containerized environments (Azure Container Apps) by verifying the async event loop is active before spawning tasks.

#### Scenario: Pipeline stages kick off after task creation
- **WHEN** a dev task is created via `POST /api/dev`
- **THEN** the pipeline stages SHALL begin executing in the background within 1 second
- **AND** each stage transition SHALL be logged with a correlation ID

#### Scenario: Pipeline execution in production container environment
- **WHEN** a dev task is created in an Azure Container Apps deployment
- **THEN** the background task SHALL execute reliably regardless of container scaling events
- **AND** if the background task fails to spawn, the task status SHALL be set to "failed" with a descriptive error

### Requirement: Development Task Artifacts
The system SHALL store and serve artifacts produced during pipeline execution.

#### Scenario: Screenshot artifacts
- **WHEN** the Test stage produces screenshots
- **THEN** screenshots SHALL be stored as base64-encoded data in the task's artifacts list
- **AND** each artifact SHALL have a name, type ("screenshot"), and data field

#### Scenario: Code archive artifact
- **WHEN** the Test stage completes successfully
- **THEN** the generated source code SHALL be compressed as a .tar.gz file
- **AND** stored in `.data/dev/{task_id}.tar.gz`
- **AND** a download endpoint `GET /api/dev/{id}/download` SHALL serve the archive

### Requirement: Development Task Persistence
The system SHALL persist dev tasks to JSON files for local development and to Cosmos DB when available.

#### Scenario: Data survives restart
- **WHEN** the backend restarts
- **THEN** previously created dev tasks are loaded from disk and available via API

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
The Turbo Dev Agent SHALL support configurable skills that provide domain-specific knowledge for code generation. Skills are managed via the SkillsService and selected per dev task.

#### Scenario: Skills from local directory
- **WHEN** the dev agent initializes
- **THEN** it SHALL use SkillsService to scan `.agents/skills/` for installed skill definitions
- **AND** include relevant skill instructions as context in code generation prompts based on the task's `skillIds`

#### Scenario: List installed skills
- **WHEN** `GET /api/agents/skills` is called
- **THEN** the system SHALL return a list of installed skills with name, description, version, file count, and source

#### Scenario: Install marketplace skill
- **WHEN** `POST /api/agents/skills/install` is called with repo and skill name
- **THEN** the system SHALL run `npx skills add` in the background and install the skill to `.agents/skills/`

#### Scenario: Delete installed skill
- **WHEN** `DELETE /api/agents/skills/{name}` is called
- **THEN** the system SHALL remove the skill directory and return success

### Requirement: Skills Management Service
The system SHALL provide a SkillsService that manages the lifecycle of agent skills — installing, uninstalling, listing, searching, and reading skill content for prompt injection.

#### Scenario: List installed skills with metadata
- **WHEN** `GET /api/agents/skills` is called
- **THEN** the system SHALL scan `.agents/skills/` and return each skill's name, description (from SKILL.md frontmatter), version, file count, and source ("local")

#### Scenario: Install skill from skills.sh marketplace
- **WHEN** `POST /api/agents/skills/install` is called with `{repo, skillName}`
- **THEN** the system SHALL execute `npx skills add <repo> --skill <skillName> -y` as a background subprocess
- **AND** return immediately with `{status: "installing", name: <skillName>}`
- **AND** upon completion, the skill SHALL appear in the installed skills list

#### Scenario: Install skill from local path
- **WHEN** `POST /api/agents/skills/install-local` is called with `{sourcePath, name}`
- **THEN** the system SHALL copy the directory at sourcePath into `.agents/skills/<name>/`
- **AND** validate that a SKILL.md file exists in the source
- **AND** return the installed skill metadata

#### Scenario: Uninstall skill
- **WHEN** `DELETE /api/agents/skills/{name}` is called
- **THEN** the system SHALL remove the `.agents/skills/<name>/` directory
- **AND** return `{success: true}`

#### Scenario: Search marketplace
- **WHEN** `GET /api/agents/skills/search?q=<query>` is called
- **THEN** the system SHALL execute `npx skills find <query>` and parse the output
- **AND** return `{results: [{name, repo, url, description}]}`

### Requirement: Per-Project Skill Selection for Dev Tasks
The DevTask model SHALL support selecting which installed skills the Dev Agent uses during code generation for that specific task.

#### Scenario: Create dev task with skills
- **WHEN** a dev task is created with `skillIds: ["react-native-expo", "voice-live"]`
- **THEN** the task SHALL store the selected skill IDs
- **AND** the Dev Agent SHALL load and inject the content of those skills into Plan and Build prompts

#### Scenario: Auto-suggest skills for spec
- **WHEN** `GET /api/dev/suggest-skills?specId=<id>` is called
- **THEN** the system SHALL match the spec content keywords against installed skill descriptions
- **AND** return the top-3 most relevant skill names

#### Scenario: Skill content injection in pipeline
- **WHEN** the Dev Agent runs a Plan or Build stage for a task with selected skills
- **THEN** it SHALL read each selected skill's SKILL.md and key reference files
- **AND** append condensed skill context (max ~2000 tokens per skill) to the generation prompt
- **AND** the total skill context SHALL NOT exceed 6000 tokens

