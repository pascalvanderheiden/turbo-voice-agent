# Tasks: Deploy to Azure with Managed Identity

## Phase 1: Dockerfiles
- [x] Create `backend/Dockerfile` — Python 3.12 slim, install dependencies from pyproject.toml, copy app, expose port 8000, run uvicorn (no --reload), install ffmpeg for video stitching
- [x] Create `frontend/Dockerfile` — Node 22 alpine, install deps, build Next.js standalone, copy .next/standalone + .next/static + public, expose port 3000, run node server.js
- [x] Test Docker builds locally: `docker build -t turbo-backend ./backend` and `docker build -t turbo-frontend ./frontend`

## Phase 2: Bicep Infrastructure
- [x] Create `infra/main.bicep` — orchestrate all modules, accept parameters (location, resourceGroupName, cosmosDbThroughput, etc.)
- [x] Create `infra/main.parameters.json` — default parameter values
- [x] Create `infra/modules/container-registry.bicep` — ACR Basic SKU with admin disabled (use managed identity)
- [x] Create `infra/modules/cosmos-db.bicep` — Cosmos DB NoSQL account (provisioned throughput 400 RU/s, session consistency, continuous backup), database `turbovoice`, containers: notes, ideas, research, specs with `/userId` partition key
- [x] Create `infra/modules/storage.bicep` — Storage account + Azure Files share for persistent data (videos, uploads, JSON files)
- [x] Create `infra/modules/ai-foundry-eastus2.bicep` — AI Foundry instance in East US 2 with model deployments: gpt-5.2, gpt-4.1, gpt-4o-realtime-preview, gpt-5.3-codex, sora-2
- [x] Create `infra/modules/ai-foundry-westus.bicep` — AI Foundry instance in West US with model deployment: o3-deep-research
- [x] Create `infra/modules/container-apps-env.bicep` — Container Apps Environment with Log Analytics workspace
- [x] Create `infra/modules/container-app-backend.bicep` — Backend container app: min replicas 1, system-assigned managed identity, Azure Files volume mount at /mnt/data, env vars (endpoints, deployment names, DATA_DIR=/mnt/data), ingress on port 8000 (external, WebSocket idle timeout 30 min)
- [x] Create `infra/modules/container-app-frontend.bicep` — Frontend container app: min replicas 1, system-assigned managed identity, env var NEXT_PUBLIC_API_URL pointing to backend ingress FQDN, ingress on port 3000 (external)
- [x] Create `infra/modules/rbac.bicep` — Role assignments: backend MI → Cosmos DB Built-in Data Contributor, backend MI → Cognitive Services OpenAI User (both Foundry instances), backend MI → Storage File Data SMB Share Contributor, both MIs → AcrPull on ACR

## Phase 3: azd Configuration
- [x] Create `azure.yaml` — azd project descriptor with backend and frontend services, hooks for Docker build + push to ACR, Bicep infra path
- [x] Add `.azure/` to `.gitignore` if not present
- [x] Test `azd init` and `azd provision` locally (dry-run)

## Phase 4: Managed Identity Auth Changes
- [x] Update `backend/app/agents/config.py` — replace `api_key=` with `azure_ad_token_provider` using `DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default")`; fall back to API key if `AZURE_OPENAI_API_KEY` env var is set (local dev compatibility)
- [x] Update `backend/app/services/research_client.py` — same pattern: use token provider when no API key env var, fall back to key for local dev
- [x] Update `backend/app/agents/marketing_agent.py` — Sora-2 REST calls: acquire token via `DefaultAzureCredential` when `SORA_API_KEY` is not set; fall back to key for local dev
- [x] Update `backend/app/routes/voice_ws.py` — Voice Live WebSocket: use managed identity token as `access_token` query param when `VOICE_LIVE_API_KEY` is not set; fall back to `api-key` header for local dev

## Phase 5: Environment & Documentation
- [x] Update `backend/.env.example` with all production env vars (no key vars, endpoints only)
- [x] Update `frontend/.env.example` with `NEXT_PUBLIC_API_URL`
- [x] Update `README.md` — add Azure deployment section: prerequisites, `azd up` instructions, architecture diagram, resource list, managed identity explanation
- [x] Update `openspec/project.md` — fill in Infrastructure & Deployment section (azd + Bicep)
