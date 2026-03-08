# Change: Add Voice Agent Foundation

## Why

Turbo Voice Agent needs its core foundation: a real-time voice interface (web + iOS) backed by an agentic team that can execute tasks on the user's behalf. The first use case is notes management — users can create, read, update, and delete notes via voice or directly through the app UI. This establishes the end-to-end architecture (Voice Live → Supervisor → Agent → Cosmos DB) that all future agents and capabilities will build upon.

## What Changes

- **Real-time voice backend**: FastAPI WebSocket endpoint proxying audio to/from Azure Voice Live API with function calling support, enabling the voice agent to delegate tasks to the agent team
- **Agent orchestration**: Microsoft Agent Framework supervisor agent that receives function calls from the voice session and routes them to the appropriate specialist agent
- **Notes agent**: First specialist agent — handles CRUD operations for notes, registered as a tool on the supervisor
- **Notes service layer**: Cosmos DB NoSQL service with dual auth (DefaultAzureCredential + emulator), partition key strategy, and parameterized queries
- **Web frontend**: Next.js 15 dashboard with Turbo Agent branding, notes management UI (list, create, edit, delete), and a voice mode with animated voice orb
- **iOS mobile app**: React Native 0.82+ / Expo SDK 52+ app with notes management and voice mode, matching web feature parity

## Impact

- Affected specs: `realtime-voice`, `agent-orchestration`, `notes-service`, `web-app`, `mobile-app` (all new)
- Affected code: New `backend/`, `frontend/`, `mobile/` project directories
- External dependencies: Azure Voice Live API, Azure Cosmos DB (emulator for local), Microsoft Agent Framework (`agent-framework` Python package)
- Infrastructure: Cosmos DB emulator in Docker for local development
