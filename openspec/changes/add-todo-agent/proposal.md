## Why

The app currently manages notes, ideas, research, specs, and dev tasks — all stored in Cosmos DB. However, users already maintain their to-do lists in **Microsoft To-Do**, and duplicating that data in our database would create sync headaches and a fragmented experience. By adding a Todo Agent backed by the **Microsoft To-Do MCP server**, users get a unified task management experience: voice-driven or manual to-do management that reads and writes directly to their existing Microsoft To-Do account — zero data duplication.

## What Changes

- **New Todo Agent**: A specialist agent (`TodoAgent`) that defines tool functions for CRUD operations on Microsoft To-Do tasks (create, list, get, update, delete, mark complete). Unlike other agents, this agent does **not** use a Cosmos DB service layer — it delegates all operations to the Microsoft To-Do MCP server.
- **Microsoft To-Do MCP server integration**: Backend integration with the `microsoft-todo` MCP server for reading/writing tasks. The agent communicates with Microsoft To-Do via the MCP protocol, and the MCP server handles the Microsoft Graph API calls.
- **Microsoft Account connection flow**: An "Authenticate Once" button in the user menu that initiates Microsoft Account OAuth consent, granting the MCP server delegated access to manage the user's Microsoft To-Do on their behalf. Connection status is persisted in the user profile.
- **Supervisor routing**: Register the Todo Agent in the SupervisorAgent with its function set so voice and chat sessions can create/manage to-dos.
- **Agent status update**: Expose the Todo Agent and its `microsoft-todo` MCP server in the `/api/agents/status` endpoint so the agent graph visualization shows the new agent and its MCP dependency.
- **Frontend Todos page**: A new `/todos` page for manual to-do management (list, create, edit, complete, delete) — following the same patterns as the notes page but backed entirely by API calls that proxy to Microsoft To-Do.
- **Backend REST routes**: `/api/todos` routes that proxy CRUD operations through the Todo Agent to the MCP server (no Cosmos DB persistence).
- **GPT-5.2 model**: The Todo Agent uses the `gpt-5.2` model for function calling, as specified.

## Capabilities

### New Capabilities
- `todo-agent`: The specialist agent with tool definitions for Microsoft To-Do task management, MCP server integration, and supervisor routing.
- `todo-mcp-connection`: Microsoft Account OAuth connection flow (authenticate-once button in user menu), MCP server configuration, and connection status tracking in user profile.
- `todo-ui`: Frontend todos page for manual to-do management and API routes that proxy to the Todo Agent.

### Modified Capabilities
- `agent-orchestration`: Add Todo Agent registration in SupervisorAgent, add todo function routing, and expose the agent + MCP server in the agent status endpoint.
- `web-app`: Add todos navigation item to sidebar and user menu, add the authenticate-once connection section to the user menu.

## Impact

- **Backend**: New files: `agents/todo_agent.py`, `routes/todos.py`, `mcp/todo_mcp_client.py`. Modified: `agents/supervisor.py`, `main.py` (lifespan + agent status), `routes/user.py` (connection status).
- **Frontend**: New files: `app/(app)/todos/page.tsx`. Modified: `lib/api.ts` (todosApi + connection API), `components/layout/user-menu.tsx` (authenticate button), sidebar navigation, agent page (auto via API).
- **Dependencies**: Microsoft To-Do MCP server package, Microsoft Graph OAuth scopes for Tasks.ReadWrite.
- **Infrastructure**: MCP server configuration. May need additional Entra ID app registration scopes for Microsoft To-Do consent.
- **No database changes**: To-do data lives entirely in Microsoft To-Do — no new Cosmos DB containers or models.
