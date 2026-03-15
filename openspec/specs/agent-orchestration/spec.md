## MODIFIED Requirements

### Requirement: Supervisor routes function calls to specialist agents
The SupervisorAgent SHALL maintain a routing table that maps function names to specialist agents. The routing table SHALL include todo-related functions (`create_todo`, `get_todos`, `get_todo`, `update_todo`, `delete_todo`, `complete_todo`) mapped to the TodoAgent.

#### Scenario: Supervisor routes create_todo to TodoAgent
- **WHEN** `handle_function_call("create_todo", ...)` is called on the supervisor
- **THEN** it SHALL route to the TodoAgent and return `(result, "Todo Agent")`

#### Scenario: Supervisor includes TodoAgent in constructor
- **WHEN** the SupervisorAgent is initialized in `main.py` lifespan
- **THEN** it SHALL accept an optional `todo_agent: TodoAgent | None` parameter

### Requirement: Agent status endpoint includes all agents
The `/api/agents/status` endpoint SHALL include the TodoAgent in the agents list with its tool definitions and MCP server information.

#### Scenario: Agent status includes todo agent
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include an agent entry with `{"id": "todo", "name": "Todo Agent", "type": "specialist", "model": "gpt-5.2", "status": "active", "tools": ["create_todo", "get_todos", "get_todo", "update_todo", "delete_todo", "complete_todo"], "mcpServers": ["microsoft-todo"]}`

#### Scenario: Agent graph includes edge from supervisor to todo
- **WHEN** `GET /api/agents/status` is called
- **THEN** the edges array SHALL include `{"from": "supervisor", "to": "todo"}`
