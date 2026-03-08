# Turbo Voice Agent

Real-time conversational AI voice agent with notes management. Built with Azure Voice Live API, Microsoft Agent Framework, and Cosmos DB.

## Architecture

```
Client (Web/iOS) → WebSocket → FastAPI → Voice Live API
                                  ↓
                            Supervisor Agent
                                  ↓
                            Notes Agent → Cosmos DB
```

- **Backend**: Python/FastAPI with Azure Voice Live, Microsoft Agent Framework
- **Web**: Next.js 15, Tailwind CSS v4, shadcn/ui-style components
- **Mobile**: React Native 0.82+ / Expo SDK 52+ (iOS)
- **Database**: Azure Cosmos DB (local emulator via Docker)

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for Cosmos DB emulator)
- Azure OpenAI resource with `gpt-4o`, `gpt-4o-realtime-preview`, and `sora-2` deployments

## Quick Start

### 1. Start Cosmos DB Emulator

```bash
docker compose up -d
```

Wait for the emulator to be healthy (~30s):
```bash
docker compose ps
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your Azure OpenAI and Voice Live credentials

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload --port 8000
```

### 3. Web Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. iOS Mobile App

```bash
cd mobile
cp .env.example .env
npm install
npx expo start --ios
```

## Environment Variables

### Backend (`.env`)

| Variable | Description |
|---|---|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint (default: `https://localhost:8081`) |
| `COSMOS_KEY` | Cosmos DB key (emulator key pre-filled; omit in production for managed identity) |
| `COSMOS_DATABASE` | Database name (default: `turbovoice`) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI / AI Foundry endpoint (East US 2) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key (omit in production for managed identity) |
| `AZURE_OPENAI_DEPLOYMENT` | Primary model deployment (default: `gpt-5.2`) |
| `AZURE_OPENAI_SEARCH_DEPLOYMENT` | Web search model deployment (default: `gpt-4.1`) |
| `AZURE_OPENAI_WESTUS_ENDPOINT` | Azure OpenAI / AI Foundry endpoint (West US) |
| `AZURE_OPENAI_WESTUS_API_KEY` | West US API key (omit in production for managed identity) |
| `AZURE_OPENAI_DEEP_RESEARCH_DEPLOYMENT` | Deep research model (default: `o3-deep-research`) |
| `VOICE_LIVE_ENDPOINT` | Voice Live WebSocket endpoint |
| `VOICE_LIVE_DEPLOYMENT` | Realtime model deployment name |
| `VOICE_LIVE_API_KEY` | Voice Live API key (omit in production for managed identity) |
| `DEV_CODEX_DEPLOYMENT` | Codex model for dev agent (default: `gpt-5.3-codex`) |
| `SORA_ENDPOINT` | Azure AI Foundry endpoint for Sora-2 (defaults to `AZURE_OPENAI_ENDPOINT`) |
| `SORA_API_KEY` | API key for Sora-2 (omit in production for managed identity) |
| `SORA_DEPLOYMENT` | Sora-2 deployment name (default: `sora-2`) |
| `DATA_DIR` | Persistent data directory (default: `data`, production: `/mnt/data`) |

### Frontend (`.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |

## Deploy to Azure

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- An Azure subscription

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Azure Container Apps Environment                            │
│ ┌─────────────────────┐   ┌──────────────────────────────┐ │
│ │ Frontend (Next.js)  │──▶│ Backend (FastAPI + WebSocket) │ │
│ │ Port 3000           │   │ Port 8000                     │ │
│ └─────────────────────┘   └──────┬───────────────────────┘ │
└──────────────────────────────────┼──────────────────────────┘
                                   │ Managed Identity (RBAC)
                  ┌────────────────┼────────────────┐
                  ▼                ▼                 ▼
         Azure Cosmos DB    AI Foundry         Azure Files
         (Provisioned)      East US 2 / West US  (Persistent)
```

### Azure Resources Provisioned

| Resource | Purpose |
|----------|---------|
| Container Apps Environment | Hosts backend + frontend containers |
| Azure Cosmos DB (Provisioned 400 RU/s) | Database — always on, no cold starts |
| Azure Container Registry | Docker image storage |
| Azure Files | Persistent storage for videos, uploads, data |
| AI Foundry (East US 2) | gpt-5.2, gpt-4.1, gpt-4o-realtime, gpt-5.3-codex, sora-2 |
| AI Foundry (West US) | o3-deep-research |
| Log Analytics | Centralized logging |

### Deploy

```bash
# Login to Azure
azd auth login

# Provision infrastructure and deploy
azd up
```

This will:
1. Create all Azure resources via Bicep
2. Build and push Docker images to ACR
3. Deploy backend + frontend containers
4. Configure managed identity and RBAC (no API keys)

### Managed Identity

In production, all `*_API_KEY` and `*_KEY` environment variables are **omitted**. The app auto-detects managed identity via `DefaultAzureCredential`:
- **Cosmos DB**: Built-in Data Contributor role
- **AI Foundry**: Cognitive Services OpenAI User role (both regions)
- **Storage**: File Data SMB Share Contributor role
- **ACR**: AcrPull role

## Project Structure

```
├── backend/                  # Python/FastAPI backend
│   └── app/
│       ├── agents/           # Supervisor + Notes agent
│       ├── db/               # Cosmos DB client + init
│       ├── models/           # Pydantic models
│       ├── routes/           # REST + WebSocket endpoints
│       ├── services/         # NotesService (CRUD)
│       └── voice/            # Voice Live session + handler
├── frontend/                 # Next.js 15 web app
│   └── src/
│       ├── app/              # Pages (dashboard, notes, voice)
│       ├── components/       # UI components (sidebar, orb)
│       └── lib/              # API client, hooks, utils
├── mobile/                   # Expo/React Native iOS app
│   └── app/                  # Screens (notes, voice)
├── docker-compose.yml        # Cosmos DB emulator
└── openspec/                 # Specifications
```

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest
```

## Features

- **Voice Mode**: Real-time voice conversations via Azure Voice Live API
- **Notes Management**: Create, read, update, delete notes via UI or voice
- **Agent Framework**: Supervisor agent routes tasks to specialist agents
- **Cross-Platform**: Web (Next.js) and iOS (Expo) with shared backend
