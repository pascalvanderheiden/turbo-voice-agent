# Design: Deploy to Azure with Managed Identity

## Context
The app is a two-tier architecture: Next.js 15 frontend (standalone) + FastAPI backend with WebSocket voice proxy, asyncio background tasks, and file storage. It connects to Azure Cosmos DB and two Azure AI Foundry instances (East US 2 + West US). The Azure subscription does not allow API keys — all services must use managed identity with RBAC.

## Goals
- Deploy all components to Azure with zero-downtime production readiness
- Managed identity for all service-to-service auth (no keys)
- Cosmos DB always-on (provisioned throughput, no sleep)
- Both AI Foundry instances with all model deployments provisioned via IaC
- azd-compatible deployment with Bicep infrastructure-as-code

## Non-Goals
- CI/CD pipeline setup (GitHub Actions) — separate concern
- Custom domain / SSL certificate configuration — done post-deployment
- Auto-scaling tuning — start with sensible defaults
- Mobile app deployment — web only

## Decisions

### Container Apps Environment Architecture
- **What**: Single Container Apps Environment with two apps (backend + frontend)
- **Why**: Shared VNet, internal DNS, low-latency communication between frontend and backend
- **Backend**: min replicas = 1 (always-on for WebSocket voice sessions), max = 3
- **Frontend**: min replicas = 1, max = 3
- **Ingress**: Backend exposed internally + externally (API + WebSocket), frontend exposed externally only

### File Storage via Azure Files Volume Mount
- **What**: Azure Files share mounted at `/mnt/data` (backend) for video, uploads, JSON persistence
- **Why**: Persistent across container restarts, no code changes needed (just set `DATA_DIR=/mnt/data`), supports concurrent reads
- **Trade-off**: Azure Files has higher latency than local SSD but acceptable for this workload (video writes are infrequent)

### Managed Identity Token Acquisition
- **What**: Use `azure.identity.aio.DefaultAzureCredential` with `get_token("https://cognitiveservices.azure.com/.default")` for OpenAI services
- **Pattern for SDK clients**: `AzureOpenAI(azure_ad_token_provider=get_bearer_token)`
- **Pattern for REST calls (Sora-2)**: Acquire token via credential, use as `Authorization: Bearer <token>`
- **Pattern for WebSocket (Voice)**: Acquire token, pass as query param `access_token` instead of `api-key` header
- **Cosmos DB**: Already uses `DefaultAzureCredential` in production mode — no change needed

### IaC Structure (Bicep + azd)
```
infra/
├── main.bicep                    # Entry point, orchestrates all modules
├── main.parameters.json          # Parameter defaults
├── modules/
│   ├── container-apps-env.bicep  # Container Apps Environment + Log Analytics
│   ├── container-app-backend.bicep
│   ├── container-app-frontend.bicep
│   ├── cosmos-db.bicep           # Cosmos account + database + containers
│   ├── container-registry.bicep  # ACR
│   ├── storage.bicep             # Storage account + file share
│   ├── ai-foundry-eastus2.bicep  # AI Foundry + model deployments
│   ├── ai-foundry-westus.bicep   # AI Foundry + model deployments
│   └── rbac.bicep                # All role assignments
azure.yaml                       # azd project descriptor
backend/Dockerfile                # Python 3.12 + uvicorn
frontend/Dockerfile               # Node 22 + Next.js standalone
```

### Cosmos DB Configuration
- **SKU**: Provisioned throughput (not serverless) — always-on guarantee
- **Throughput**: 400 RU/s per container (autoscale to 4000 RU/s optional)
- **Consistency**: Session (default, sufficient for single-user-per-session pattern)
- **Containers**: `notes`, `ideas`, `research`, `specs` — all with `/userId` partition key
- **Backup**: Continuous backup (7-day point-in-time restore)

### RBAC Role Assignments
| Identity | Resource | Role |
|----------|----------|------|
| Backend Container App (system MI) | Cosmos DB account | Cosmos DB Built-in Data Contributor |
| Backend Container App (system MI) | AI Foundry East US 2 | Cognitive Services OpenAI User |
| Backend Container App (system MI) | AI Foundry West US | Cognitive Services OpenAI User |
| Backend Container App (system MI) | Storage account | Storage File Data SMB Share Contributor |
| Backend Container App (system MI) | Container Registry | AcrPull |
| Frontend Container App (system MI) | Container Registry | AcrPull |

## Risks / Trade-offs
- **Risk**: AI Foundry model deployments via Bicep may have regional availability constraints → Mitigation: validate model availability before deployment
- **Risk**: WebSocket connections through Container Apps ingress may have idle timeout limits (default 4 min) → Mitigation: configure idle timeout to 30 min for voice sessions
- **Risk**: Azure Files latency for video file writes → Mitigation: acceptable for infrequent large writes; consider Blob Storage + FUSE mount if latency becomes an issue
- **Trade-off**: Provisioned throughput costs more than serverless but guarantees always-on with no cold starts

## Open Questions
- None — requirements are clear (managed identity, always-on, two Foundry instances)
