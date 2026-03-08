## MODIFIED Requirements

### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, and spec agents.

#### Scenario: Route spec functions
- **WHEN** a function call with name matching spec operations (create_spec, get_specs, get_spec, update_spec, delete_spec, generate_spec, optimize_spec) is received
- **THEN** the supervisor routes it to the Spec Agent and returns the result with agent name "Spec Agent"

#### Scenario: Route unknown function
- **WHEN** a function call with an unknown name is received
- **THEN** the supervisor returns an error mentioning it can help with notes, ideas, research, and specs

### Requirement: Agent Function Tools for Voice
The Supervisor SHALL accept an optional spec_agent parameter and register it alongside notes, brainstorm, and research agents. All registered agent tool definitions SHALL be exposed.

#### Scenario: All tools exposed
- **WHEN** the supervisor is initialized with all four specialist agents
- **THEN** tool_definitions includes tools from notes, brainstorm, research, and spec agents
