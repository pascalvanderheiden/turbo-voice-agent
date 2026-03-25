# Verbal — History

## Project Context
Turbo Voice Agent — Azure infrastructure and DevOps.
Stack: Bicep IaC, Azure Container Apps, ACI sandbox, GitHub Actions CI/CD, Docker.
User: Pascal van der Heiden.

Infrastructure: Azure Container Apps for backend + frontend, ACI for sandbox containers, Cosmos DB, Azure Storage for skills, ACR for container images. Deployed via `azd up`.

## Work Queue

### 2026-03-25T20:47 — Fenster Local Dev Fixes Ready for Deploy

Fenster completed 6 backward-compatible fixes to backend local-dev fallbacks:
- PPTX MIME type in upload endpoint
- PDF export/download fallback to local storage
- ACI sandbox init guard with silent fallback
- Sandbox pre-flight health check with actionable message
- Skills service connection error logging (debug level)
- Blob storage error logging reduction

**Files modified:** `backend/app/routes/upload.py`, `backend/app/agents/dev_agent.py`, `backend/app/services/aci_sandbox_service.py`, `backend/app/services/skills_service.py`, `backend/app/services/slides_service.py`

**Action:** Ready for Verbal to commit and run `azd deploy` (backend only).

## Learnings

### Deployment: Local Dev Fixes (2025-01-23)
Committed and deployed Fenster's local dev fallbacks (commit de81b4d):
- ACI sandbox init wrapped in try/except for missing credentials
- Sandbox pre-flight reachability check with actionable error messages
- PPTX MIME type support added to upload endpoint
- PDF export/download falls back to local file storage when blob unavailable
- Skills/blob storage errors demoted to debug/warning level
- ACI polling optimized: 2s intervals, split provisioning logic

Both backend and frontend deployed successfully to Azure via `azd deploy`. No issues encountered.
Deployments target Azure Container Apps with latest container images.
