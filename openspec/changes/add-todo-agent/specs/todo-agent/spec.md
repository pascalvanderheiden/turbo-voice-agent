## ADDED Requirements

### Requirement: Todo Agent class
The system SHALL provide a `TodoAgent` class in `backend/app/agents/todo_agent.py` that follows the established agent pattern with `tool_definitions` property and `handle_function_call()` method. The agent SHALL use the `gpt-5.2` model.

#### Scenario: Agent exposes tool definitions
- **WHEN** the supervisor queries the TodoAgent's `tool_definitions` property
- **THEN** it SHALL return OpenAI-compatible function schemas for: `create_todo`, `get_todos`, `get_todo`, `update_todo`, `delete_todo`, `complete_todo`

#### Scenario: Agent handles create_todo
- **WHEN** `handle_function_call("create_todo", {"title": "Buy groceries"}, user_id)` is called
- **THEN** the agent SHALL invoke the Microsoft To-Do MCP server to create a task and return a JSON string with `{"success": true, "todo": {"id": "...", "title": "Buy groceries", "isCompleted": false}}`

#### Scenario: Agent handles get_todos
- **WHEN** `handle_function_call("get_todos", "{}", user_id)` is called
- **THEN** the agent SHALL invoke the MCP server to list tasks and return a JSON string with `{"todos": [...]}`

#### Scenario: Agent handles complete_todo
- **WHEN** `handle_function_call("complete_todo", {"todo_id": "abc"}, user_id)` is called
- **THEN** the agent SHALL invoke the MCP server to mark the task as completed and return a JSON string with `{"success": true, "todo": {"id": "abc", "isCompleted": true}}`

#### Scenario: Agent handles MCP server unavailable
- **WHEN** the MCP server is not available or the user has not authenticated
- **THEN** the agent SHALL return a JSON string with `{"error": "Microsoft To-Do is not connected. Please authenticate in your profile settings."}`

### Requirement: MCP client integration
The system SHALL provide an MCP client module at `backend/app/mcp/todo_mcp_client.py` that manages communication with the Microsoft To-Do MCP server process. The client SHALL pass the user's stored OAuth token per-request for user-scoped operations.

#### Scenario: MCP client invokes tool
- **WHEN** the TodoAgent calls `mcp_client.call_tool("create_task", {"title": "Buy groceries"}, user_token)` 
- **THEN** the MCP client SHALL send the tool invocation to the MCP server with the user's delegated token and return the result

#### Scenario: MCP client handles connection failure
- **WHEN** the MCP server process is not running or unreachable
- **THEN** the MCP client SHALL raise an exception that the TodoAgent catches and converts to an error JSON response

### Requirement: Supervisor routing for todo functions
The SupervisorAgent SHALL route todo-related function calls (`create_todo`, `get_todos`, `get_todo`, `update_todo`, `delete_todo`, `complete_todo`) to the TodoAgent.

#### Scenario: Voice session creates a todo
- **WHEN** a voice session triggers `create_todo` via function calling
- **THEN** the supervisor SHALL route to the TodoAgent and return the result with agent name "Todo Agent"

#### Scenario: Supervisor includes todo tools in aggregated definitions
- **WHEN** the supervisor aggregates all agents' tool_definitions for voice/chat sessions
- **THEN** the todo agent's 6 tool definitions SHALL be included in the aggregated list
