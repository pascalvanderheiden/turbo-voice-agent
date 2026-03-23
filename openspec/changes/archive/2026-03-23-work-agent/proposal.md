## Why

The agent architecture currently covers notes, brainstorm, research, specs, dev, slides, marketing, skills, and todos — but lacks a dedicated agent for workplace intelligence. Users need to query work-related information (emails, meetings, documents, Teams messages) via voice or chat without leaving the app. Microsoft's WorkIQ MCP server provides this capability through a single `ask_work_iq` operation.

## What Changes

- Add a new **Work Agent** (specialist) that connects to the WorkIQ MCP server (`https://github.com/microsoft/work-iq`)
- Register the agent in the supervisor for routing from voice and chat
- Add Microsoft Work Account OAuth connection flow (same pattern as Microsoft To-Do)
- Add "Connect Work Account" button on the settings page
- Add the agent to the agents page (architecture diagram + card)
- No dedicated UI page needed — interactions happen exclusively via voice and chat

## Capabilities

### New Capabilities
- `work-agent`: Work Agent specialist that queries Microsoft 365 data (emails, meetings, documents, Teams messages) via the WorkIQ MCP server. Includes agent class, MCP client, tool definitions, and supervisor routing.
- `work-account-connection`: Microsoft Work Account OAuth connection flow for WorkIQ access. Follows the same pattern as the existing Microsoft To-Do connection (OAuth consent, token storage, settings page button).

### Modified Capabilities
- `agent-orchestration`: Supervisor gains routing for work agent function calls (`ask_work_question`)

## Impact

- **Backend**: New `WorkAgent` class + `WorkMcpClient`, new OAuth endpoints at `/api/me/connections/work-account`, supervisor updated with work agent routing
- **Frontend**: Settings page gains "Connect Work Account" button, agents page gains icon/color mapping for `work` agent
- **Infrastructure**: New env vars `WORKIQ_OAUTH_CLIENT_ID`, `WORKIQ_OAUTH_TENANT_ID`; may share the existing Entra app registration
- **Dependencies**: WorkIQ MCP server npm package
