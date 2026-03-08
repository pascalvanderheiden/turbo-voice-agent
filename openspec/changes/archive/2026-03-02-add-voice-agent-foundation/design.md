## Context

This is the foundational architecture for Turbo Voice Agent. It establishes the full vertical slice: voice input → agent orchestration → business logic → database, plus direct UI interaction for the same operations. The design must support future agents being added with minimal changes to the voice or orchestration layers.

### Stakeholders
- End users (web + iOS) interacting via voice or UI
- Developers extending the agent team with new specialist agents

## Goals / Non-Goals

### Goals
- Real-time, low-latency voice conversations via Azure Voice Live API
- Supervisor-based agent routing so the voice layer doesn't need to know about individual agents
- Notes CRUD accessible via both voice commands and direct UI
- Local-first development using Cosmos DB emulator in Docker
- Turbo Agent branding applied consistently across web and iOS
- Web and iOS feature parity for notes management and voice mode

### Non-Goals
- Production Azure deployment (local only for now)
- User authentication / multi-tenancy (single-user local mode)
- Offline support or local caching
- RAG / vector search capabilities (future work)
- Avatar integration for voice (future work)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Clients (Web / iOS)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Notes UI    │  │  Voice Orb   │  │  WebSocket   │      │
│  │  (CRUD)      │  │  (States)    │  │  (Audio)     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         │ REST API        │ WS connect       │ Audio stream  │
└─────────┼─────────────────┼──────────────────┼───────────────┘
          │                 │                  │
┌─────────▼─────────────────▼──────────────────▼───────────────┐
│                     FastAPI Backend                           │
│  ┌──────────────┐  ┌────────────────────────────────────┐   │
│  │  REST Routes  │  │  Voice WebSocket Endpoint           │   │
│  │  /api/notes   │  │  /ws/voice                          │   │
│  └──────┬───────┘  │  ┌──────────────────────────────┐   │   │
│         │          │  │  Azure Voice Live SDK         │   │   │
│         │          │  │  (audio ↔ speech ↔ model)     │   │   │
│         │          │  │  Function calling → Supervisor │   │   │
│         │          │  └──────────────┬───────────────┘   │   │
│         │          └─────────────────┼───────────────────┘   │
│         │                            │                        │
│         │          ┌─────────────────▼───────────────────┐   │
│         │          │  Supervisor Agent                    │   │
│         │          │  (Microsoft Agent Framework)         │   │
│         │          │  Routes to specialist agents         │   │
│         │          └─────────────────┬───────────────────┘   │
│         │                            │                        │
│         │          ┌─────────────────▼───────────────────┐   │
│         │          │  Notes Agent                         │   │
│         │          │  Tools: create/read/update/delete    │   │
│         │          └─────────────────┬───────────────────┘   │
│         │                            │                        │
│         ▼                            ▼                        │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              Notes Service Layer                       │   │
│  │  _doc_to_model() / _model_to_doc()                    │   │
│  └───────────────────────────┬───────────────────────────┘   │
│                              │                                │
│  ┌───────────────────────────▼───────────────────────────┐   │
│  │         Cosmos DB Client (Singleton)                   │   │
│  │  Dual auth: DefaultAzureCredential / Emulator key     │   │
│  └───────────────────────────┬───────────────────────────┘   │
└──────────────────────────────┼────────────────────────────────┘
                               │
                  ┌────────────▼────────────┐
                  │    Azure Cosmos DB      │
                  │    (Emulator / Azure)   │
                  │    Database: turbovoice │
                  │    Container: notes     │
                  │    Partition: /userId   │
                  └─────────────────────────┘
```

## Decisions

### 1. Voice Live with Function Calling (not Agent Quickstart)
- **Decision**: Use Voice Live Model Quickstart with function calling to bridge to the Agent Framework, rather than the Agent Quickstart (Foundry Agent) approach
- **Why**: The Agent Quickstart ties directly to a Foundry-hosted agent. We want the supervisor to live in our backend so we control routing and can add agents without redeploying Foundry resources
- **Alternative**: Foundry Agent Quickstart — rejected because it couples voice directly to a single agent and limits local development

### 2. Supervisor Pattern with GraphWorkflow
- **Decision**: Use Microsoft Agent Framework's `GraphWorkflow` with a supervisor agent node that routes to specialist agent nodes
- **Why**: Clean separation — the voice layer only knows about the supervisor; new agents are added as graph nodes with edges from the supervisor
- **Alternative**: Direct function-per-agent on Voice Live — rejected because it doesn't scale and mixes concerns

### 3. WebSocket Proxy Architecture
- **Decision**: Client connects to our FastAPI WebSocket (`/ws/voice`), which proxies audio to Azure Voice Live
- **Why**: Keeps Azure credentials server-side; allows us to intercept function calls and route them through the agent framework; works identically for web and iOS clients
- **Alternative**: Client connects directly to Voice Live — rejected because it exposes credentials and bypasses the agent framework

### 4. Cosmos DB Partition Strategy
- **Decision**: Partition key `/userId` on the notes container, using a hardcoded default user ID for local development
- **Why**: Prepares for multi-tenancy while keeping local development simple; all queries are partition-scoped
- **Alternative**: No partition key / synthetic key — rejected because it doesn't align with future multi-user support

### 5. Shared Notes Service
- **Decision**: Both REST API routes and the notes agent use the same `NotesService` class
- **Why**: Single source of truth for business logic; voice and UI operations are guaranteed consistent
- **Alternative**: Separate implementations — rejected because it leads to drift

### 6. Audio Format
- **Decision**: PCM16 at 24kHz for all audio streaming (client ↔ backend ↔ Voice Live)
- **Why**: Best quality supported by Voice Live; consistent format avoids transcoding
- **Alternative**: Opus/WebM — rejected because Voice Live expects PCM16

## Data Model

### Note Document (Cosmos DB)
```json
{
  "id": "uuid",
  "userId": "default-user",
  "title": "Meeting Notes",
  "content": "Discussed project timeline...",
  "docType": "note",
  "createdAt": "2026-03-01T12:00:00Z",
  "updatedAt": "2026-03-01T12:30:00Z"
}
```

### Pydantic Models (Five-Tier)
- `NoteBase` — shared fields (title, content)
- `NoteCreate` — creation request
- `NoteUpdate` — partial update (all optional)
- `Note` — API response (includes id, timestamps)
- `NoteInDB` — internal (includes docType, userId)

## Risks / Trade-offs

- **Risk**: Voice Live API latency depends on Azure region and model choice → **Mitigation**: Use `gpt-realtime` model for lowest latency; configure ServerVad with tuned thresholds
- **Risk**: WebSocket proxy adds hop → **Mitigation**: Minimal processing in proxy; audio forwarded as raw bytes
- **Risk**: Cosmos DB emulator requires Docker → **Mitigation**: Document setup clearly; provide docker-compose
- **Risk**: Agent Framework is preview (`0.1.0-preview`) → **Mitigation**: Wrap in thin abstraction; pin version

## Open Questions

- Voice selection: Should we expose multiple voice personas, or start with a single default voice (Ava)?
- Error UX: How should voice errors (connection lost, API timeout) be communicated — voice orb state only, or toast notification too?
