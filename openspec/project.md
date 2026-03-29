# Project Context

## Purpose
Turbo Voice Agent is a real-time conversational AI voice agent (general purpose). It provides speech-to-speech interaction using Azure Voice Live API, backed by the Microsoft Agent Framework and Azure AI Foundry for intelligent, agentic behavior. The project targets both web and mobile platforms.

## Tech Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: Azure Cosmos DB (NoSQL API) with vector search — local dev via Cosmos DB Linux emulator in Docker
- **AI/Agents**: Microsoft Agent Framework, Azure AI Foundry
- **Voice**: Azure Voice Live API (WebSocket-based real-time speech-to-speech)

### Frontend — Web
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **UI Library**: shadcn/ui (new-york style)
- **Styling**: Tailwind CSS v4
- **Icons**: Tabler Icons

### Frontend — Mobile
- **Framework**: React Native 0.82+ with Expo SDK 52+
- **Architecture**: New Architecture (Fabric/TurboModules) — mandatory
- **Language**: TypeScript

### Infrastructure & Deployment
- **Cloud**: Microsoft Azure
- **Deployment**: azd (Azure Developer CLI) with Bicep IaC
- **Hosting**: Azure Container Apps (backend + frontend)
- **Database**: Azure Cosmos DB NoSQL (provisioned throughput, always-on)
- **File Storage**: Azure Files (mounted as volume on Container Apps)
- **AI**: Azure AI Foundry (East US 2 + West US)
- **Auth**: Managed Identity with RBAC (no API keys in production)
- **CI/CD**: GitHub Actions

### Network Topology
- **CAE VNet** (`vnet-cae`, `10.2.0.0/16`): Hosts Container Apps and private endpoints
  - `snet-cae-infra` (`10.2.0.0/23`) — Container Apps Environment infrastructure subnet
  - `snet-private-endpoints` (`10.2.2.0/24`) — Private endpoints (Cosmos DB)
  - `snet-reserved` (`10.2.3.0/24`) — Reserved for future use
- **ACI VNet** (`10.1.0.0/16`): Sandbox VNet for Azure Container Instances
- **VNet Peering**: Bidirectional peering between CAE VNet and ACI VNet
- **Cosmos DB Private Endpoint**: In `snet-private-endpoints`, with private DNS zone `privatelink.documents.azure.com` for automatic A-record registration. Public access is disabled (Azure Policy requirement). Backend connects via `DefaultAzureCredential` — DNS handles routing transparently, no code changes needed.

### Branding
- **Identity**: Turbo Agent
- **Color Palette**: Hot pink (`#E91E8C`), Cyan (`#00D4FF`), Purple (`#7B2FBE`)
- **Background**: Dark mode default (`#0F0F1A` base)
- **Typography**: Inter (UI) + JetBrains Mono (code)
- **Logo**: `assets/turbo-agent-logo.png` (transparent PNG)

## Project Conventions

### Code Style
- **Python**: PEP 8, type hints on all public functions, `ruff` for linting and formatting
- **TypeScript**: Strict mode, ESLint + Prettier, named exports preferred
- **Naming**: snake_case (Python), camelCase (TypeScript), PascalCase (React components)
- **Imports**: Absolute imports preferred; group stdlib → third-party → local
- **Comments**: Only when clarifying non-obvious logic; avoid restating code

### Architecture Patterns
- **Backend**: Service layer pattern — FastAPI routes → service classes → Cosmos DB
- **Authentication**: Dual auth (DefaultAzureCredential for Azure, connection string for local emulator)
- **Frontend**: Server Components by default (Next.js), Client Components only when needed
- **State**: React Context / Zustand for client state; server state via React Query or SWR
- **Voice**: WebSocket connection for real-time audio streaming with turn detection
- **Agents**: Microsoft Agent Framework for orchestration; function calling for VoiceRAG

### Testing Strategy
- **Python**: pytest with async support, parameterized queries, TDD pattern for service layers
- **TypeScript**: Vitest for unit tests, Playwright for E2E
- **Mobile**: Jest + React Native Testing Library
- **Coverage**: Aim for ≥80% on service layers and critical paths

### Git Workflow
- **Branching**: Feature branches off `main`, PR-based merges
- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
- **Co-author**: Always include `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` when AI-assisted
- **Specs**: Use OpenSpec proposal workflow for new features and breaking changes

## Domain Context
- **Voice Live**: Azure's WebSocket-based API for real-time bidirectional speech; supports noise suppression, echo cancellation, turn detection, and function calling
- **Agentic Voice**: The agent can invoke tools/functions during conversation (e.g., search, database lookups) via function calling — this is the VoiceRAG pattern
- **Cosmos DB Vector Search**: Native DiskANN-based vector indexing for semantic search within the document store
- **Microsoft Agent Framework**: Orchestrates multi-step agent workflows, tool use, and memory

## Important Constraints
- Azure Voice Live requires WebSocket connections — plan for connection lifecycle management
- Cosmos DB emulator runs on Linux containers only; requires Docker for local development
- React Native New Architecture is mandatory for Expo SDK 52+ — no legacy bridge support
- Dark mode is the default and primary design target; light mode is secondary
- All Azure services must support DefaultAzureCredential for production auth

## External Dependencies
- **Azure Voice Live API** — real-time speech-to-speech
- **Azure AI Foundry** — model hosting and agent infrastructure
- **Azure Cosmos DB** — document store with vector search
- **Azure AI Search** — optional, for RAG retrieval patterns
- **GitHub Copilot SDK** — optional, for copilot-powered features hosted on Azure
