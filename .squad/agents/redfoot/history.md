# Redfoot — History

## Project Context

- **Project:** turbo-voice-agent — Real-time conversational AI voice agent with multi-agent orchestration
- **User:** the project maintainer
- **Stack:** Python 3.12/FastAPI backend, Next.js 15 frontend, React Native/Expo mobile, Azure (Cosmos DB, Voice Live, Container Apps), Bicep IaC
- **OpenSpec workflow:** propose → explore → implement → archive
- **Active changes:** `openspec/changes/` (optimize-slides-pipeline, skills-hot-reload)
- **Spec library:** 40+ specs in `openspec/specs/` covering features from notes-service to squad-visualization
- **Archive:** Completed changes in `openspec/changes/archive/`

## Learnings

- Joined the team 2026-03-29. Ready to manage the OpenSpec lifecycle.
- Archived `cosmos-private-networking` (16/16 tasks, all complete). Change moved to `openspec/changes/archive/`. Created new spec `openspec/specs/cosmos-private-networking/spec.md` covering VNet, private endpoint, DNS zone, CAE VNet integration, public access disable, and VNet peering. Merged 2 new scenarios into existing `openspec/specs/azure-infrastructure/spec.md` (VNet peering connectivity + private endpoint access for sandbox state). Pattern: when a change touches an existing spec domain, merge new scenarios rather than overwriting — keeps the spec library as the canonical source of truth.
- Proposed `open-source-project` change (2026-03-29). Comprehensive OSS release prep covering: README rewrite with deployment instructions, screenshot, personal reference scrubbing, MIT license, CODE_OF_CONDUCT.md, SECURITY.md, Bicep parameter genericization, GitHub Actions cleanup, .gitignore audit, repo metadata updates, decommission + redeployment validation. Created 4 specs: `oss-documentation` (9 requirements for deployment/contribution docs), `oss-governance` (4 requirements for license/CoC/security), `deployment-decommission` (3 requirements for Azure teardown), and delta spec for `azure-infrastructure` (6 new requirements for parameter genericization). Generated 86 tasks across 15 groups. Pattern: OSS releases require multi-layered scrubbing (automated grep + manual audit) and validation via decommission → clean redeploy cycle to ensure reproducibility.
