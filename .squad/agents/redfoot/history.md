# Redfoot — History

## Project Context

- **Project:** turbo-voice-agent — Real-time conversational AI voice agent with multi-agent orchestration
- **User:** Pascal van der Heiden
- **Stack:** Python 3.12/FastAPI backend, Next.js 15 frontend, React Native/Expo mobile, Azure (Cosmos DB, Voice Live, Container Apps), Bicep IaC
- **OpenSpec workflow:** propose → explore → implement → archive
- **Active changes:** `openspec/changes/` (optimize-slides-pipeline, skills-hot-reload)
- **Spec library:** 40+ specs in `openspec/specs/` covering features from notes-service to squad-visualization
- **Archive:** Completed changes in `openspec/changes/archive/`

## Learnings

- Joined the team 2026-03-29. Ready to manage the OpenSpec lifecycle.
- Archived `cosmos-private-networking` (16/16 tasks, all complete). Change moved to `openspec/changes/archive/`. Created new spec `openspec/specs/cosmos-private-networking/spec.md` covering VNet, private endpoint, DNS zone, CAE VNet integration, public access disable, and VNet peering. Merged 2 new scenarios into existing `openspec/specs/azure-infrastructure/spec.md` (VNet peering connectivity + private endpoint access for sandbox state). Pattern: when a change touches an existing spec domain, merge new scenarios rather than overwriting — keeps the spec library as the canonical source of truth.
