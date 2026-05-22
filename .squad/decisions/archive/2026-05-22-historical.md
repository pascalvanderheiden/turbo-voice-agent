## Historical Decisions

### Local Dev Graceful Degradation

**Author:** Fenster  
**Date:** 2025-07-24  
**Status:** Implemented

Follow the existing dual-implementation pattern (Cosmos DB + InMemory fallback) for all Azure-dependent services:
- ACI sandbox init: try/except fallback to static `SANDBOX_URL`
- Pipeline sandbox check: pre-flight health check with actionable message
- Blob storage errors: downgraded from `exception()` to `warning()` logging
- Sandbox skill sync: connection errors at `debug` level
- PPTX upload: added MIME type to `/api/upload`

**Rules:** Never use `logger.exception()` for expected-absent infrastructure; connection errors from local services → `debug`; all changes backward-compatible.

### ACI Sandbox Cold-Start Optimizations

**Author:** Fenster  
**Date:** 2025-07-14  
**Status:** Implemented

Optimized provisioning latency:
- Health poll interval: 5s → 2s
- Fast poll after ARM Succeeded: 0.5s
- Split provisioning API: `start_provisioning()` + `wait_until_ready()`
- Slides pipeline overlap: concurrent content gathering with ACI provisioning
- Progress callbacks: status messages to pipeline terminal

**Files:** `backend/app/services/aci_sandbox_service.py`, `backend/app/agents/dev_agent.py`

### Slides Pipeline Restructured to init→slides→run

**Author:** Fenster  
**Date:** 2025-01-20  
**Status:** Implemented

Pipeline stages changed from `["init", "skills", "slides"]` to `["init", "slides", "run"]`:
- Skills sync merged into init (prerequisite, not user-visible)
- Slides stage uses `copilot --autopilot --yolo` shell command
- Run stage owns dev server lifecycle: `npm install` → `npm run dev` → health check → auto-register
- PowerPoint handling consolidated into slides prompt
- Default theme/palette: `default`/`blue`

**Impact:** Frontend stage display names updated; tests referencing old `"skills"` stage name updated.

### Slides Preview Auto-Shows on Run Stage Completion

**Author:** McManus  
**Date:** 2025-07-25  
**Status:** Implemented

Slides preview iframe auto-displays when `run` stage completes using `/api/dev/{task_id}/preview/`. Fallback "Start Preview" button remains for edge cases. Refresh and Stop buttons available.

**Impact:** Frontend only—no backend API contract change. Both `development/page.tsx` and `development/[id]/page.tsx` updated.

### Cosmos DB Private Networking Architecture

**Author:** Verbal  
**Date:** 2025-07-25  
**Status:** Implemented (IaC only — deployment pending)

Cosmos DB now uses a private endpoint for data-plane traffic. VNet peering connects CAE and ACI sandbox networks.

**Key Architecture:**
- CAE VNet (10.2.0.0/16) with 3 subnets
- Private endpoint for Cosmos DB (privatelink.documents.azure.com DNS zone)
- Bidirectional VNet peering between CAE VNet and ACI sandbox VNet
- Public access disabled on Cosmos DB account

**Files Changed:** `infra/modules/vnet-cae.bicep`, `cosmos-private-endpoint.bicep`, `vnet-peering.bicep`, `container-apps-env.bicep`, `cosmos-db.bicep`, `main.bicep`

### Model Preference Directive

**Author:** Project Maintainer
**Date:** 2026-03-29T10:35:13Z  
**Status:** Active

Use `claude-opus-4.6` as the preferred model for all squad agent spawns. Do not use `claude-sonnet-4.5` as default.
