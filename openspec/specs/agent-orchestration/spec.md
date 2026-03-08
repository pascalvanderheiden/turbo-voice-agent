# agent-orchestration Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, spec, dev, skills, and marketing agents. All function calls SHALL include the authenticated user's ID so that specialist agents operate on the correct user's data.

#### Scenario: Route marketing functions
- **WHEN** a function call with name matching marketing operations (create_marketing_video, get_marketing_videos, get_marketing_video, delete_marketing_video, trigger_video_generation) is received
- **THEN** the supervisor routes it to the Marketing Agent and returns the result with agent name "Marketing Agent"

#### Scenario: User context passed to agents
- **WHEN** the supervisor receives a function call from an authenticated session
- **THEN** the supervisor SHALL pass the user_id to the specialist agent
- **AND** the agent SHALL scope all data operations to that user

### Requirement: Per-User Data Isolation
All backend services SHALL scope data operations to the authenticated user's ID. No user SHALL be able to access, modify, or delete another user's data.

#### Scenario: Notes scoped to user
- **WHEN** a user calls `GET /api/notes`
- **THEN** the service SHALL return only notes belonging to the authenticated user's ID

#### Scenario: Cross-user access prevented
- **WHEN** a user attempts to access a resource (note, idea, spec, dev task, marketing video) belonging to another user
- **THEN** the API SHALL return HTTP 404 (not found) rather than 403 to avoid leaking resource existence

### Requirement: Backend Auth Middleware
The backend SHALL validate Entra ID JWT access tokens on all `/api/*` endpoints and reject unauthenticated requests with HTTP 401.

#### Scenario: Valid token accepted
- **WHEN** a request includes a valid Bearer token from the turboagent.nl tenant
- **THEN** the middleware SHALL extract the user's object ID (oid) and inject it as user_id into the request context

#### Scenario: Missing or invalid token rejected
- **WHEN** a request has no Authorization header or an invalid/expired token
- **THEN** the middleware SHALL return HTTP 401 with error detail "Authentication required"

#### Scenario: Wrong tenant rejected
- **WHEN** a token from a non-turboagent.nl tenant is presented
- **THEN** the middleware SHALL return HTTP 401 with error detail "Invalid tenant"

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
Agent function tools SHALL be exposed to Voice Live sessions and be callable during conversations. All Azure OpenAI and AI Foundry service calls SHALL authenticate via managed identity (DefaultAzureCredential) when no API key environment variable is set, falling back to API key for local development.

#### Scenario: Voice tool invocation
- **WHEN** Voice Live invokes a function tool during a conversation
- **THEN** the supervisor routes it to the correct specialist agent and returns the result

#### Scenario: Managed identity authentication for AI services
- **WHEN** the backend runs in Azure with a system-assigned managed identity
- **AND** no `AZURE_OPENAI_API_KEY` environment variable is set
- **THEN** all Azure OpenAI SDK clients SHALL use `azure_ad_token_provider` with `DefaultAzureCredential`
- **AND** all direct REST API calls (Sora-2) SHALL use a Bearer token acquired from `DefaultAzureCredential`
- **AND** Voice Live WebSocket connections SHALL use `access_token` query parameter with a managed identity token

#### Scenario: API key fallback for local development
- **WHEN** the backend runs locally with `AZURE_OPENAI_API_KEY` set
- **THEN** all Azure OpenAI SDK clients SHALL use the API key directly
- **AND** Voice Live WebSocket SHALL use the `api-key` header

### Requirement: Skills Agent
The system SHALL include a Skills Agent as a specialist agent registered in the supervisor routing. The Skills Agent handles skill installation, uninstallation, search, and listing via function calling, enabling voice and chat users to manage skills through natural language.

#### Scenario: Route skills functions
- **WHEN** a function call with name matching skills operations (install_skill, uninstall_skill, search_skills, list_skills) is received
- **THEN** the supervisor SHALL route it to the Skills Agent and return the result with agent name "Skills Agent"

#### Scenario: Skills agent in status
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include the Skills Agent with id "skills", type "specialist", and its tool definitions

### Requirement: Marketing Agent Registration
The Marketing Agent SHALL be registered in the agent overview with model info and tool definitions.

#### Scenario: Agent overview includes Marketing Agent
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include a marketing agent entry with model "sora-2 (Azure AI Foundry, East US 2)", scriptModel "gpt-5.2", and its tool list
- **AND** an edge from supervisor to marketing SHALL be present in the topology

### Requirement: Marketing Agent Voice Tools
The Marketing Agent's tool definitions SHALL be included in the voice WebSocket session tools.

#### Scenario: Voice session includes marketing tools
- **WHEN** a voice WebSocket session is established
- **THEN** the available tools SHALL include create_marketing_video, get_marketing_videos, get_marketing_video, delete_marketing_video, and trigger_video_generation

