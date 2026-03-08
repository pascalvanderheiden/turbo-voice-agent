## MODIFIED Requirements

### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, spec, and dev agents. The dev agent's tool definitions SHALL include mode selection for pipeline triggers.

#### Scenario: Route dev functions
- **WHEN** a function call with name matching dev operations (create_dev_task, get_dev_tasks, get_dev_task, delete_dev_task, trigger_dev_pipeline) is received
- **THEN** the supervisor routes it to the Dev Agent and returns the result with agent name "Dev Agent"

#### Scenario: Route spec functions
- **WHEN** a function call with name matching spec operations (create_spec, get_specs, get_spec, update_spec, delete_spec, generate_spec, optimize_spec) is received
- **THEN** the supervisor routes it to the Spec Agent and returns the result with agent name "Spec Agent"

#### Scenario: Route unknown function
- **WHEN** a function call with an unknown name is received
- **THEN** the supervisor returns an error mentioning it can help with notes, ideas, research, specs, and development

### Requirement: Agent Function Tools for Voice
The Supervisor SHALL accept all specialist agents including dev_agent and register their tool definitions. All registered agent tool definitions SHALL be exposed.

#### Scenario: All tools exposed
- **WHEN** the supervisor is initialized with all specialist agents
- **THEN** tool_definitions includes tools from notes, brainstorm, research, spec, and dev agents
