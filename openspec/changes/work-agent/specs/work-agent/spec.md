## ADDED Requirements

### Requirement: Work Agent class
The system SHALL provide a `WorkAgent` specialist class that connects to the WorkIQ MCP server and exposes a single tool for querying Microsoft 365 workplace data.

#### Scenario: Agent initialization
- **WHEN** the application starts
- **THEN** the system SHALL create a `WorkAgent` instance with a `WorkMcpClient` and a token resolver callable

#### Scenario: Tool definitions
- **WHEN** the supervisor requests the work agent's tool definitions
- **THEN** the agent SHALL return a single tool `ask_work_question` with parameters: `question` (string, required) and `file_urls` (array of strings, optional)

#### Scenario: Handle function call — connected user
- **WHEN** `handle_function_call("ask_work_question", ...)` is called and the user has a valid work account connection
- **THEN** the agent SHALL resolve the user's refresh token, call WorkIQ's `ask_work_iq` operation, and return the response as JSON

#### Scenario: Handle function call — no connection
- **WHEN** `handle_function_call("ask_work_question", ...)` is called and the user has no work account connection
- **THEN** the agent SHALL return an error message instructing the user to connect their work account in Settings

### Requirement: WorkMcpClient
The system SHALL provide a `WorkMcpClient` class that communicates with the WorkIQ MCP server.

#### Scenario: Token refresh
- **WHEN** a query is made with a refresh token
- **THEN** the client SHALL exchange the refresh token for an access token via the Microsoft OAuth token endpoint with scopes `offline_access Mail.Read Calendars.Read Files.Read.All Chat.Read User.Read`

#### Scenario: Ask question
- **WHEN** `ask(question, token, file_urls)` is called
- **THEN** the client SHALL invoke the WorkIQ `ask_work_iq` tool and return the response text and conversation ID

### Requirement: Agent status registration
The system SHALL include the work agent in the `/api/agents/status` endpoint response with `id: "work"`, `type: "specialist"`, `model: "gpt-5.2"`, `mcpServers: ["work-iq"]`, and tool `ask_work_question`.

#### Scenario: Agent status includes work agent
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include a work agent entry and a `supervisor → work` edge

### Requirement: Frontend agent display
The system SHALL display the work agent on the agents page with an appropriate icon and color in both the architecture diagram and agent card grid.

#### Scenario: Agent icon and color mapping
- **WHEN** the agents page renders
- **THEN** the work agent SHALL use `IconBriefcase` icon and `var(--color-brand-cyan)` color
