## ADDED Requirements

### Requirement: Skills Agent
The system SHALL include a Skills Agent as a specialist agent registered in the supervisor routing. The Skills Agent handles skill installation, uninstallation, search, and listing via function calling, enabling voice and chat users to manage skills through natural language.

#### Scenario: Route skills functions
- **WHEN** a function call with name matching skills operations (install_skill, uninstall_skill, search_skills, list_skills) is received
- **THEN** the supervisor SHALL route it to the Skills Agent and return the result with agent name "Skills Agent"

#### Scenario: Skills agent in status
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include the Skills Agent with id "skills", type "specialist", and its tool definitions

## MODIFIED Requirements

### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, spec, dev, and skills agents. The dev agent's tool definitions SHALL include mode selection for pipeline triggers.

#### Scenario: Route dev functions
- **WHEN** a function call with name matching dev operations (create_dev_task, get_dev_tasks, get_dev_task, delete_dev_task, trigger_dev_pipeline) is received
- **THEN** the supervisor routes it to the Dev Agent and returns the result with agent name "Dev Agent"

#### Scenario: Route skills functions
- **WHEN** a function call with name matching skills operations (install_skill, uninstall_skill, search_skills, list_skills) is received
- **THEN** the supervisor routes it to the Skills Agent and returns the result with agent name "Skills Agent"

#### Scenario: Route spec functions
- **WHEN** a function call with name matching spec operations (create_spec, get_specs, get_spec, update_spec, delete_spec, generate_spec, optimize_spec) is received
- **THEN** the supervisor routes it to the Spec Agent and returns the result with agent name "Spec Agent"

#### Scenario: Route unknown function
- **WHEN** a function call with an unknown name is received
- **THEN** the supervisor returns an error mentioning it can help with notes, ideas, research, specs, development, and skills
