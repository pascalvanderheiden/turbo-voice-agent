# Delta Spec: agent-orchestration

## MODIFIED Requirements

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
