## Context

The turbo-voice-agent has 11 specialist agents connected via a supervisor. The Todo Agent established the pattern for MCP-backed agents with Microsoft OAuth: agent class → MCP client → Graph API, with OAuth flow endpoints and settings page connection button. The Work Agent follows this identical pattern but connects to the WorkIQ MCP server for Microsoft 365 workplace intelligence (emails, meetings, documents, Teams messages).

## Goals / Non-Goals

**Goals:**
- Add Work Agent as a specialist routed from supervisor (voice + chat)
- Connect to WorkIQ MCP server via single `ask_work_iq` operation
- Reuse the Microsoft To-Do OAuth pattern for Work Account connection
- Show agent on agents page (architecture + card)
- Settings page button to connect/disconnect Work Account

**Non-Goals:**
- No dedicated UI page for the work agent (voice/chat only)
- No custom work data visualization or dashboards
- No caching of WorkIQ responses
- No offline/mock implementation for local dev beyond a stub response

## Decisions

### Decision 1: Reuse Entra App Registration
Reuse the existing `ENTRA_CLIENT_ID` app registration with additional Graph API scopes for WorkIQ (`Mail.Read`, `Calendars.Read`, `Files.Read.All`, `Chat.Read`, `User.Read`). This avoids a second app registration. The OAuth flow uses a separate connection key (`work-account`) to store a distinct refresh token.

**Alternative**: Separate app registration — rejected because it adds infra complexity for no benefit.

### Decision 2: WorkMcpClient wraps WorkIQ npm package
Create `WorkMcpClient` following the same pattern as `TodoMcpClient`. Since WorkIQ exposes a single `ask_work_iq` operation, the client is simpler — just token refresh + a single call method. The agent exposes one tool: `ask_work_question`.

**Alternative**: Direct HTTP calls to Graph API — rejected because WorkIQ already handles the complex multi-source aggregation.

### Decision 3: Supervisor routing via single function name
The supervisor routes `ask_work_question` to the work agent. This is simple since there's only one tool. The agent is accessible from both voice and chat gateways through the existing supervisor routing mechanism.

### Decision 4: Parallel OAuth storage pattern
Store work account refresh token alongside todo token in the user profile document. Use `workRefreshToken` / `workConnectedAt` fields (mirroring `todoRefreshToken` / `todoConnectedAt`). The in-memory cache uses `work:{user_id}` key prefix.

## Risks / Trade-offs

- **[Risk]** WorkIQ scope requirements may change → Mitigation: Use `offline_access` + broad read scopes; update scopes in env var if needed
- **[Risk]** Token expiry during long voice sessions → Mitigation: Same refresh flow as Todo, tokens refreshed on each call
- **[Trade-off]** Single tool (`ask_work_question`) keeps it simple but limits structured queries → Accept: WorkIQ handles query interpretation internally
