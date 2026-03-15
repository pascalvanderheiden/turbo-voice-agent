## 1. MCP Client Infrastructure

- [x] 1.1 Create `backend/app/mcp/todo_mcp_client.py` with MCP client class that communicates with the Microsoft To-Do MCP server process — supports `call_tool(tool_name, args, user_token)` and connection health checks
- [x] 1.2 Add MCP server configuration to backend settings (server process command, environment variables, connection params)
- [x] 1.3 Initialize MCP client in `main.py` lifespan and handle graceful startup/shutdown of the MCP server process

## 2. Microsoft Account OAuth Connection

- [x] 2.1 Add connection endpoints to `backend/app/routes/user.py`: `POST /api/me/connections/microsoft-todo` (initiate OAuth), `GET /api/auth/callback/microsoft-todo` (handle callback), `GET /api/me/connections/microsoft-todo` (status), `DELETE /api/me/connections/microsoft-todo` (disconnect)
- [x] 2.2 Implement token exchange, encrypted storage of refresh token in user profile document (Cosmos DB or in-memory), and token retrieval for MCP client usage
- [x] 2.3 Add `connectionsApi` to `frontend/src/lib/api.ts` with `microsoftTodo.status()`, `microsoftTodo.connect()`, `microsoftTodo.disconnect()` methods
- [x] 2.4 Add "Connected Accounts" section to `frontend/src/components/layout/user-menu.tsx` with "Connect Microsoft To-Do" / "Connected" states and disconnect option

## 3. Todo Agent

- [x] 3.1 Create `backend/app/agents/todo_agent.py` with `TodoAgent` class: `tool_definitions` property (create_todo, get_todos, get_todo, update_todo, delete_todo, complete_todo) and `handle_function_call()` that delegates to the MCP client
- [x] 3.2 Configure the Todo Agent to use the `gpt-5.2` model in `backend/app/agents/config.py`
- [x] 3.3 Register `TodoAgent` in `backend/app/agents/supervisor.py`: add constructor parameter, add `todo_functions` routing set, add routing logic in `handle_function_call()`, include tools in aggregated definitions

## 4. Backend REST Routes

- [x] 4.1 Create `backend/app/routes/todos.py` with REST endpoints: `GET /api/todos`, `GET /api/todos/{id}`, `POST /api/todos`, `PUT /api/todos/{id}`, `DELETE /api/todos/{id}` — all proxying through the TodoAgent
- [x] 4.2 Add todo route service injection pattern (`set_todo_agent()`, `_get_agent()`) and register routes in `main.py`
- [x] 4.3 Add connection check middleware/guard that returns 503 when user has not connected Microsoft To-Do

## 5. Agent Status & Visualization

- [x] 5.1 Update `/api/agents/status` in `main.py` to include the Todo Agent entry with id, name, type, model (gpt-5.2), tools, and `mcpServers: ["microsoft-todo"]`
- [x] 5.2 Add supervisor → todo edge in the agent graph edges array

## 6. Frontend Todos Page

- [x] 6.1 Create `frontend/src/app/(app)/todos/page.tsx` with list view (task cards showing title, completion checkbox, due date), empty state, and "not connected" prompt
- [x] 6.2 Add create todo dialog/form (title, optional due date, optional notes)
- [x] 6.3 Add edit todo functionality (inline or modal editing of title, notes, due date)
- [x] 6.4 Add complete/uncomplete toggle with visual feedback (strikethrough, muted styling)
- [x] 6.5 Add delete todo with confirmation dialog
- [x] 6.6 Add `todosApi` to `frontend/src/lib/api.ts` with `list()`, `get(id)`, `create(data)`, `update(id, data)`, `delete(id)` methods
- [x] 6.7 Add "To-Dos" navigation item to sidebar with checklist icon, linking to `/todos`

## 7. Integration & Testing

- [x] 7.1 Add unit tests for `TodoAgent.handle_function_call()` with mocked MCP client
- [x] 7.2 Add unit tests for connection endpoints (OAuth flow, status, disconnect)
- [x] 7.3 Add unit tests for `/api/todos` routes with mocked TodoAgent
- [x] 7.4 Wire up full integration in `main.py` lifespan: MCP client → TodoAgent → SupervisorAgent, todo routes injection
- [x] 7.5 Add i18n translation keys for todos page (title, create, edit, delete, empty state, not connected) in EN and NL
