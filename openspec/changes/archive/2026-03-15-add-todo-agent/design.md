## Context

The Turbo Voice Agent app currently has 7 specialist agents (Notes, Brainstorm, Research, Spec, Dev, Skills, Marketing), all following the same pattern: agent class → service layer → Cosmos DB. Each agent exposes `tool_definitions` and `handle_function_call()`, and the SupervisorAgent routes voice/chat function calls to the right specialist.

The Todo Agent breaks this pattern intentionally: **to-do data lives in Microsoft To-Do, not Cosmos DB**. Instead of a service layer that talks to a database, the Todo Agent delegates to a **Microsoft To-Do MCP server** that handles Microsoft Graph API calls. This means no data models, no Cosmos containers, no in-memory fallback — just an agent that speaks MCP.

The user must grant the app delegated access to their Microsoft To-Do account. This is a one-time OAuth consent flow ("Authenticate Once") surfaced in the user menu. Once connected, the MCP server can act on the user's behalf for all to-do operations.

**Current state:**
- Agent architecture is well-established with clear patterns
- MCP server concept exists (Playwright is listed in agent status) but no active MCP client integration in the function call pipeline
- User menu has profile info, photo upload, theme toggle, language selector, and logout
- The `/api/agents/status` endpoint already supports `mcpServers` array per agent

## Goals / Non-Goals

**Goals:**
- Add a Todo Agent that manages Microsoft To-Do tasks via MCP server integration
- Enable one-time Microsoft Account authentication for To-Do access from the user menu
- Provide a manual to-do management page in the frontend (list, create, edit, complete, delete)
- Register the agent in the supervisor for voice/chat routing
- Display the agent and its MCP server in the agent graph visualization
- Use GPT-5.2 model for the Todo Agent

**Non-Goals:**
- Storing to-do data in Cosmos DB (Microsoft To-Do is the single source of truth)
- Syncing or caching to-dos locally
- Supporting multiple to-do providers (only Microsoft To-Do)
- Sub-tasks, attachments, or advanced Microsoft To-Do features (lists beyond the default, recurring tasks) — keep it simple for v1
- Mobile app changes (web only for now)

## Decisions

### 1. MCP client architecture: Direct MCP client in the agent

**Decision**: The TodoAgent holds an MCP client instance that communicates with the Microsoft To-Do MCP server process. The agent's `handle_function_call()` translates our tool calls into MCP tool invocations.

**Alternatives considered**:
- *Service layer wrapping Microsoft Graph directly*: Would bypass MCP and require us to maintain Graph API integration code. MCP server handles this better and is reusable.
- *Generic MCP proxy in supervisor*: Over-engineered for a single MCP integration. Keep it agent-specific for now.

**Rationale**: The MCP server is a standalone process that manages Graph API auth and provides tool schemas. The agent acts as a thin adapter between our function call protocol and MCP. This keeps the agent lightweight and delegates complexity to the MCP server.

### 2. Authentication: Delegated OAuth consent stored in user profile

**Decision**: The "Authenticate Once" flow triggers a Microsoft OAuth consent for `Tasks.ReadWrite` scope. The resulting refresh token is stored server-side (encrypted, associated with the user profile). The MCP server uses this token for Graph API calls on behalf of the user.

**Alternatives considered**:
- *Per-session token*: Would require re-auth every session — bad UX.
- *App-only permissions*: Would require admin consent and wouldn't scope to individual users' task lists.

**Rationale**: Delegated access with a stored refresh token provides the "authenticate once" experience. The token is scoped to the user and refreshed automatically by the MCP server.

### 3. Backend routes: Thin proxy through the Todo Agent

**Decision**: REST routes at `/api/todos` call `todo_agent.handle_function_call()` directly (not through the supervisor). This keeps the REST API simple and avoids supervisor routing overhead for direct HTTP calls.

**Alternatives considered**:
- *Routes call MCP server directly*: Would bypass the agent, creating two code paths for the same operations.
- *Routes go through supervisor*: Unnecessary indirection for direct REST calls.

**Rationale**: Voice/chat goes through supervisor → agent → MCP. REST goes through routes → agent → MCP. The agent is the single integration point in both paths.

### 4. No service layer: Agent talks directly to MCP

**Decision**: Skip the service layer entirely. The TodoAgent manages the MCP client and handles all CRUD operations. No `TodoService`, no `InMemoryTodoService`.

**Rationale**: The service layer exists to abstract Cosmos DB access. Since we're not using Cosmos DB, the abstraction adds no value. The MCP server IS the service.

### 5. Frontend: Standard page pattern, no local state caching

**Decision**: The `/todos` page follows the same pattern as notes (list/detail views, mobile support) but every operation is a fresh API call. No optimistic updates or local caching.

**Rationale**: Microsoft To-Do is the source of truth. Caching creates staleness risk since users might modify to-dos from other apps (Outlook, Microsoft To-Do mobile, etc.).

### 6. Model: GPT-5.2 for the Todo Agent

**Decision**: Use the `gpt-5.2` model for the Todo Agent, as explicitly requested. This is configured in the agent's config and used for any LLM-assisted function calling.

## Risks / Trade-offs

- **[MCP server availability]** → If the Microsoft To-Do MCP server process crashes or is unavailable, all to-do operations fail. Mitigation: Health check in agent status, clear error messages, supervisor gracefully handles agent unavailability.
- **[Token expiry / revocation]** → User's Microsoft refresh token could expire or be revoked. Mitigation: Connection status check on the profile, clear "reconnect" affordance, graceful error handling that prompts re-authentication.
- **[Latency]** → Every to-do operation requires a round-trip through MCP → Graph API. Mitigation: Accept this trade-off for v1. Could add caching later if needed.
- **[Scope creep with Microsoft To-Do features]** → Microsoft To-Do has lists, sub-tasks, recurrence, attachments, etc. Mitigation: v1 focuses on the default task list with basic CRUD + complete. Explicitly a non-goal to support advanced features.
- **[Multi-user MCP server process]** → The MCP server process needs to handle per-user tokens. Mitigation: Each user's MCP connection is scoped by their stored OAuth token, passed per-request.
