# Proposal: Deploy to Azure with Managed Identity

## Why
The application currently runs locally only. It needs to be deployed to Azure for production use with managed identity and RBAC (no API keys allowed), always-on Cosmos DB, and both AI Foundry instances provisioned with their model deployments.

## What Changes

### Azure Service Selection

| Component | Azure Service | Justification |
|-----------|---------------|---------------|
| Backend (FastAPI, Python 3.12+) | **Azure Container Apps** | WebSocket support for voice proxy, asyncio background tasks, managed identity, auto-scaling, persistent volume mounts |
| Frontend (Next.js 15, standalone) | **Azure Container Apps** | Standalone mode requires Node.js server (not static), same Container Apps environment as backend for low-latency internal communication |
| Database | **Azure Cosmos DB NoSQL (Provisioned throughput, 400 RU/s)** | Already in the app, provisioned throughput = always-on (no cold start, no sleep), DefaultAzureCredential already supported |
| File Storage | **Azure Files** (mounted as volume on Container Apps) | Videos, uploads, dev archives stored at `data/` and `uploads/` — volume mount means zero code changes |
| AI (East US 2) | **Azure AI Foundry** | Models: gpt-5.2, gpt-4.1, gpt-4o-realtime-preview, gpt-5.3-codex, sora-2 |
| AI (West US) | **Azure AI Foundry** | Models: o3-deep-research |
| Container Registry | **Azure Container Registry** (Basic SKU) | Store backend + frontend Docker images |
| Monitoring | **Azure Log Analytics + Container Apps diagnostics** | Centralized logging for both containers |
| DNS / Ingress | **Container Apps Environment managed ingress** | HTTPS termination, custom domain support |

### Why Container Apps over alternatives
- **vs App Service**: Container Apps supports multiple containers in one environment, WebSocket sticky sessions, KEDA-based scaling, and volume mounts natively
- **vs AKS**: Overkill for two containers; Container Apps is serverless Kubernetes without cluster management
- **vs Static Web Apps**: Next.js standalone mode requires a Node.js process; SWA doesn't fully support SSR

### Managed Identity & RBAC (no API keys)
- **System-assigned managed identity** on both Container Apps
- Backend identity gets RBAC roles:
  - `Cosmos DB Built-in Data Contributor` on Cosmos DB account
  - `Cognitive Services OpenAI User` on both AI Foundry instances
  - `Storage File Data SMB Share Contributor` on Azure Files
- Minimal auth-layer code changes needed to replace API key parameters with `DefaultAzureCredential` token provider (application logic unchanged)

### Cosmos DB — Always On
- **Provisioned throughput** at 400 RU/s (minimum) — never sleeps, no cold starts
- Autoscale optional (400–4000 RU/s) if traffic varies
- Database: `turbovoice`, containers: `notes`, `ideas`, `research`, `specs` (partition key: `/userId`)

### AI Foundry Model Deployments

**East US 2 Instance:**
| Model | Deployment Name | Type |
|-------|----------------|------|
| gpt-5.2 | gpt-5.2 | Standard |
| gpt-4.1 | gpt-4.1 | Standard |
| gpt-4o-realtime-preview | gpt-4o-realtime-preview | Global Standard |
| gpt-5.3-codex | gpt-5.3-codex | Standard |
| sora-2 | sora-2 | Standard |

**West US Instance:**
| Model | Deployment Name | Type |
|-------|----------------|------|
| o3-deep-research | o3-deep-research | Standard |

### Environment Variables (Production)

**Backend Container App:**
```
COSMOS_ENDPOINT=https://<cosmos-account>.documents.azure.com:443/
COSMOS_DATABASE=turbovoice
AZURE_OPENAI_ENDPOINT=https://<eastus2-foundry>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-5.2
AZURE_OPENAI_SEARCH_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_WESTUS_ENDPOINT=https://<westus-foundry>.openai.azure.com/
AZURE_OPENAI_DEEP_RESEARCH_DEPLOYMENT=o3-deep-research
VOICE_LIVE_ENDPOINT=wss://<eastus2-foundry>.openai.azure.com/
VOICE_LIVE_DEPLOYMENT=gpt-4o-realtime-preview
DEV_CODEX_DEPLOYMENT=gpt-5.3-codex
SORA_ENDPOINT=https://<eastus2-foundry>.openai.azure.com/
SORA_DEPLOYMENT=sora-2
DATA_DIR=/mnt/data
```
Note: No `*_API_KEY` variables — all auth via managed identity.

**Frontend Container App:**
```
NEXT_PUBLIC_API_URL=https://<backend-container-app>.azurecontainerapps.io
```

## Impact
- New infrastructure: 9 Azure resources provisioned via Bicep + azd
- New IaC files: `infra/` directory with Bicep modules, `azure.yaml` for azd
- New Dockerfiles: `backend/Dockerfile`, `frontend/Dockerfile`
- Minimal code change: Auth layer in `config.py`, `research_client.py`, `marketing_agent.py`, `voice_ws.py` — replace API key with `DefaultAzureCredential` token provider
- Affected specs: `agent-orchestration` (managed identity auth), new `azure-infrastructure` capability
