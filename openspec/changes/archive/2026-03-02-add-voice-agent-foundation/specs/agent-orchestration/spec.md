## ADDED Requirements

### Requirement: Supervisor Agent
The system SHALL implement a supervisor agent using Microsoft Agent Framework that receives task requests and routes them to the appropriate specialist agent.

#### Scenario: Supervisor routes a notes task
- **WHEN** the supervisor receives a request related to notes (create, read, update, delete)
- **THEN** the supervisor SHALL route the request to the notes agent
- **AND** return the notes agent's response to the caller

#### Scenario: Supervisor handles unknown task
- **WHEN** the supervisor receives a request that no specialist agent can handle
- **THEN** the supervisor SHALL respond with a helpful message indicating the task is not yet supported

### Requirement: Agent Team Graph Workflow
The agent team SHALL be orchestrated using Microsoft Agent Framework's `GraphWorkflow` with the supervisor as the entry node.

#### Scenario: Workflow execution
- **WHEN** a task is submitted to the agent team
- **THEN** the supervisor node processes the request first
- **AND** conditionally routes to the appropriate specialist agent node based on the task type
- **AND** the specialist agent's result flows back through the supervisor to the caller

#### Scenario: Adding a new agent
- **WHEN** a new specialist agent is implemented
- **THEN** it SHALL be registered as a new node in the GraphWorkflow with an edge from the supervisor
- **AND** the supervisor's instructions SHALL be updated to include the new agent's capabilities
- **AND** no changes to the voice layer or REST API are required

### Requirement: Agent Function Tools for Voice
The supervisor agent's capabilities SHALL be exposed as function tools on the Voice Live session, enabling the voice model to invoke agent tasks.

#### Scenario: Function tools registered on Voice Live
- **WHEN** a voice session is configured
- **THEN** the Voice Live session SHALL include function tool definitions that map to the supervisor's capabilities (e.g., `manage_notes` with parameters for action and note details)

#### Scenario: Voice model invokes agent function
- **WHEN** the voice model determines the user wants to perform a notes action
- **THEN** the model SHALL call the appropriate function tool
- **AND** the function handler routes the call to the supervisor agent
