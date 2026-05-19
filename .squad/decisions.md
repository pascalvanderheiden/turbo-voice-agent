# Squad Decisions

## Active Decisions

### Open-source project decisions

**Author:** Project Maintainer (via Copilot)  
**Date:** 2026-05-19T15:26:26Z  
**Status:** Approved

Phase 1 approval for open-source-project openspec with these specifics:
1. Keep `.squad/` directory in the OSS distribution but anonymize — remove the maintainer's name from team.md and any other agent files.
2. License: MIT confirmed.
3. Git history: scan all historic commits for secrets; if found, present the maintainer with the option to rewrite history via filter-branch / git-filter-repo.
4. Decommission: The maintainer will run `azd down --force --purge` after all code changes are complete.

### Backend OSS scrub conventions

**Author:** Fenster  
**Date:** 2026-05-19  
**Status:** Implemented

- Treat `backend/.env.example` as a documentation artifact, not just a variable dump: every variable should have an inline comment telling contributors what it is and where to get it.
- Use neutral placeholders (`<your-...>`) for all Azure endpoints, IDs, and keys, and keep `AUTH_DISABLED=true` enabled in the example for local development.
- Avoid custom domains or branded email addresses in backend code comments and local mock identities when preparing OSS-facing artifacts.

### .squad/ anonymization scope

**Author:** Keaton  
**Date:** 2026-05-19  
**Status:** Proposed

For OSS preparation, maintainer-specific seeded context in `.squad/agents/*/history.md`, `.squad/team.md`, and closely related `.squad/` metadata may be revised in place even though those files normally follow an append-only convention.

**Scope:**
- Allowed: seeded header context, maintainer labels, local absolute paths, and `Requested by:` fields that expose maintainer identity.
- Preserve: later learning entries, operational history, and technical decisions unless they directly contain the maintainer's name.
- Keep `.squad/` in the repository as optional Squad metadata; do not add it to `.gitignore` for this OSS pass.

**Rationale:** This is the minimum change that keeps the team metadata reusable for future work while removing direct personal identifiers from the OSS distribution.

### README note for `.squad/`

**Author:** Keaton  
**Date:** 2026-05-19  
**Status:** Implemented

Add a short README note explaining that `.squad/` is optional project metadata used by Squad (Coordinator) for AI-assisted development workflows. Link to https://github.com/bradygaster/squad and clarify that deployment and local development do not require `.squad/`.

### McManus OSS docs decisions

**Author:** McManus  
**Date:** 2026-05-19  
**Status:** Implemented

- Used the MIT license text with a neutral copyright holder: `turbo-voice-agent contributors`.
- Used Contributor Covenant 2.1 verbatim for `CODE_OF_CONDUCT.md`, replacing the contact line with GitHub Issues/Discussions guidance.
- Wrote `SECURITY.md` around GitHub Security Advisories private reporting plus explicit acknowledgement/triage expectations.
- Rewrote the README in a deployment-first OSS structure with a Mermaid architecture diagram and a maintainer-owned screenshot placeholder.
- Standardized frontend local setup around `frontend/.env.local.example` so the README can instruct `cp .env.local.example .env.local` directly.

### Verbal OSS Infra Notes

**Author:** Verbal  
**Date:** 2026-05-19  
**Status:** Implemented

- Custom domain support is now optional end-to-end. `CUSTOM_DOMAIN_NAME` and `EXISTING_CERT_NAME` default to empty values in `infra/main.parameters.json`, so standard Container Apps hostnames work without extra setup.
- GitHub Actions deployment is re-enabled for `main` pushes and manual dispatch. The deploy job now runs when `infra/`, `azure.yaml`, `backend/`, `frontend/`, or `sandbox/` change.
- Workflow environment naming is genericized through `GITHUB_ENVIRONMENT_NAME` (optional, defaults to `production`).
- `DEPLOY_RBAC` is now driven by configuration instead of a hardcoded workflow value. Default remains `true`; `DEPLOYER_PRINCIPAL_ID` stays optional.
- History audit found 1 critical tracked file (`backend/key.pem`, commit `4fdbe03`) and 1 suspicious tracked env artifact (`frontend/.!38121!.env.local`, commit `4fdbe03`).
- OIDC is confirmed: the workflow uses `azure/login@v2` with federated credentials and `azd auth login --federated-credential-provider github`.

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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
