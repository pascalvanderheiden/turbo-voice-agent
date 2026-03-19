## ADDED Requirements

### Requirement: Squad CLI available in sandbox
The sandbox Docker image SHALL have `@bradygaster/squad-cli` installed globally via npm so that the `squad` command is available on PATH.

#### Scenario: Squad CLI is available after container start
- **WHEN** the sandbox container starts
- **THEN** running `squad --version` returns a valid version string without error

### Requirement: Squad init per dev task
The squad pipeline stage SHALL run `squad init` in the sandbox workspace directory to create a `.squad/` directory with default configuration files.

#### Scenario: Squad initialized in workspace
- **WHEN** the squad stage executes for a dev task
- **THEN** a `.squad/` directory exists in the workspace containing `team.md`, `routing.md`, `decisions.md`, and `directives.md`

### Requirement: Team generation from foundation spec
The squad stage SHALL parse the foundation spec content to determine team composition. It SHALL always include a Lead agent and a Scribe agent. It SHALL add additional agents (Frontend Dev, Backend Dev, Tester, DevOps) based on technology references found in the spec.

#### Scenario: Spec mentions React and Python
- **WHEN** the foundation spec content contains references to React/Next.js and Python/FastAPI
- **THEN** the squad team includes: Lead, Frontend Dev, Backend Dev, Tester, and Scribe

#### Scenario: Spec mentions only backend technologies
- **WHEN** the foundation spec content mentions only Python/FastAPI with no frontend references
- **THEN** the squad team includes: Lead, Backend Dev, Tester, and Scribe (no Frontend Dev)

#### Scenario: Minimal spec with no technology references
- **WHEN** the foundation spec has no identifiable technology stack
- **THEN** the squad team includes the default set: Lead, Developer, Tester, and Scribe

### Requirement: Squad hire for each agent
After team composition is determined, the squad stage SHALL run `squad hire --name <name> --role <role>` for each agent in the team.

#### Scenario: All agents hired successfully
- **WHEN** the team composition includes 4 agents
- **THEN** `squad hire` is called 4 times, once per agent, and `squad status` shows all agents active

### Requirement: Routing and directives from spec
The squad stage SHALL generate `.squad/routing.md` with work routing rules derived from the spec's capability sections, and `.squad/directives.md` with coding conventions extracted from the spec.

#### Scenario: Routing rules generated
- **WHEN** the foundation spec has sections about API endpoints and UI components
- **THEN** `.squad/routing.md` maps API work to Backend Dev and UI work to Frontend Dev

### Requirement: Squad doctor validation
After initialization and hiring, the squad stage SHALL run `squad doctor` to validate the setup integrity.

#### Scenario: Doctor check passes
- **WHEN** squad init and hire complete successfully
- **THEN** `squad doctor` reports no errors and the stage completes successfully

#### Scenario: Doctor check fails
- **WHEN** `squad doctor` reports errors
- **THEN** the stage output includes the doctor error details but does NOT fail the pipeline (warning only)
