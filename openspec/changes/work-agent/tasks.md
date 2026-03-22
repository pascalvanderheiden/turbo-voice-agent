## Tasks

### Group 1: Backend — Work Agent & MCP Client

- [x] **1.1 Create WorkMcpClient** — New file `backend/app/mcp/work_mcp_client.py`. Follow `todo_mcp_client.py` pattern: token refresh via OAuth token endpoint with scopes `offline_access Mail.Read Calendars.Read Files.Read.All Chat.Read User.Read`, single `ask(question, token, file_urls)` method that invokes WorkIQ's `ask_work_iq`. Include stub for `AUTH_DISABLED` mode.
  Files: `backend/app/mcp/work_mcp_client.py`

- [x] **1.2 Create WorkAgent class** — New file `backend/app/agents/work_agent.py`. Follow `todo_agent.py` pattern: constructor takes `WorkMcpClient` + `get_user_token` callable. Single tool definition `ask_work_question(question: str, file_urls?: list[str])`. `handle_function_call()` resolves token, calls MCP client, returns response JSON. Error message if not connected.
  Files: `backend/app/agents/work_agent.py`

### Group 2: Backend — OAuth Connection Flow

- [x] **2.1 Add Work Account OAuth endpoints** — In `backend/app/routes/user.py`, add `_work_oauth_config()`, `GET/POST/DELETE /api/me/connections/work-account`, and `GET /api/auth/callback/work-account`. Follow the exact same pattern as the Microsoft To-Do endpoints. Store tokens using `workRefreshToken`/`workConnectedAt` fields.
  Files: `backend/app/routes/user.py`
  Depends on: 1.1

- [x] **2.2 Add token resolver function** — Add `get_work_user_token()` in `user.py` following `get_todo_user_token()` pattern. Check in-memory cache (`work:{user_id}`) then Cosmos DB profile.
  Files: `backend/app/routes/user.py`

- [x] **2.3 Update user profile service** — Add `update_work_connection(user_id, refresh_token, connected_at)` method to Cosmos DB profile service.
  Files: `backend/app/services/user_profile_service.py`

### Group 3: Backend — Registration & Routing

- [x] **3.1 Register work agent in main.py** — Initialize `WorkMcpClient`, create token resolver, instantiate `WorkAgent`, pass to supervisor. Add to agent status endpoint with `id: "work"`, `mcpServers: ["workiq"]`, and `supervisor → work` edge.
  Files: `backend/app/main.py`
  Depends on: 1.2, 2.2

- [x] **3.2 Add work agent routing to supervisor** — Add `work_agent` parameter to `SupervisorAgent.__init__()`. Add `ask_work_question` to routing table. Route to `work_agent.handle_function_call()`.
  Files: `backend/app/agents/supervisor.py`
  Depends on: 1.2

- [x] **3.3 Add work agent to voice/chat tool definitions** — Supervisor's `tool_definitions` property automatically aggregates all registered agent tools, so `ask_work_question` is included once work agent is registered.
  Files: N/A (automatic via supervisor)
  Depends on: 3.2

### Group 4: Frontend — Settings & API

- [x] **4.1 Add Work Account API functions** — Add `connectionsApi.workAccount.status()`, `.connect()`, `.disconnect()` to `frontend/src/lib/api.ts` following the `microsoftTodo` pattern. Add OAuth callback proxy route.
  Files: `frontend/src/lib/api.ts`, `frontend/src/app/api/auth/callback/work-account/route.ts`

- [x] **4.2 Add Work Account connection UI to settings** — Add "Connect Work Account" button with briefcase icon, connection status display, disconnect button. Handle `?work_connected=success|error` callback params. Follow exact same pattern as Microsoft To-Do section.
  Files: `frontend/src/app/(app)/settings/page.tsx`
  Depends on: 4.1

### Group 5: Frontend — Agents Page

- [x] **5.1 Add work agent icon and color** — Add `work: IconBriefcase` to `AGENT_ICONS` and `work: "var(--color-brand-cyan)"` to `AGENT_COLORS` in agents page. Import `IconBriefcase` from tabler icons.
  Files: `frontend/src/app/(app)/agents/page.tsx`

### Group 6: Tests

- [x] **6.1 Add WorkAgent unit tests** — Test tool definitions, handle_function_call routing, error on missing token, invalid JSON handling.
  Files: `backend/tests/test_work_agent.py`
  Depends on: 1.2

- [x] **6.2 Add WorkMcpClient stub tests** — Test stub mode returns mock response, no token error, health check, lifecycle.
  Files: `backend/tests/test_work_agent.py` (combined)
  Depends on: 1.1
