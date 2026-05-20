# Squad Decisions

## Active Decisions

### Deployment Parameter Orchestrator

**Author:** Verbal  
**Date:** 2026-05-19  
**Status:** Implemented

## Context

The README instructed users to manually run `azd env new`, then `azd env set` six parameters by hand before running `azd up`. This created a poor first-run experience and was error-prone.

Example of the old manual flow:
```bash
azd env new <env-name>
azd env set ENTRA_TENANT_ID <tenant-id>
azd env set ENTRA_CLIENT_ID <client-id>
azd env set CUSTOM_DOMAIN_NAME <domain>
azd env set EXISTING_CERT_NAME <cert>
azd env set ENTRA_CLIENT_SECRET <secret>
azd env set DEPLOYER_PRINCIPAL_ID <principal-id>
azd up
```

## Decision

Create a single preprovision orchestrator script (`infra/scripts/collect-deployment-params.sh`) that:
- Runs FIRST in the preprovision phase (before region selection, before Entra setup)
- Collects ALL required and optional deployment parameters
- Uses a consistent pattern: (1) check azd env, (2) auto-discover from Azure CLI, (3) prompt if interactive, (4) persist
- Is fully idempotent — safe to run multiple times, only prompts once per param
- Has a CI guard — no prompts in GitHub Actions, only auto-discovery, fails fast with clear error messages

## Implementation

### New Script

Created `infra/scripts/collect-deployment-params.sh` with these param collection functions (in order):

1. **AZURE_SUBSCRIPTION_ID**
   - Auto-discover: `az account show --query id -o tsv`
   - If multiple subs: list via `az account list` and prompt to pick
   - Persist + run `az account set --subscription <id>`

2. **AZURE_LOCATION**
   - Check `azd env get-value AZURE_LOCATION` first (azd normally sets during `env new`)
   - Only prompt if truly empty (rare — azd usually handles this)
   - Interactive: present curated list of common regions

3. **ENTRA_TENANT_ID**
   - Auto-discover: `az account show --query tenantId -o tsv`
   - Never prompt (user is already logged in to a tenant)

4. **CUSTOM_DOMAIN_NAME**
   - Optional — prompt once: "Custom domain (leave empty to use Container Apps default):"
   - Empty string is valid and persisted

5. **EXISTING_CERT_NAME**
   - Optional — only prompt if CUSTOM_DOMAIN_NAME is non-empty

6. **ENTRA_CLIENT_SECRET**
   - Optional — prompt once with explanation ("Only needed for Microsoft To Do OAuth — press Enter to skip")
   - Use `azd env set --secret` if available, else regular `azd env set`

7. **DEPLOYER_PRINCIPAL_ID**
   - Auto-discover: `az ad signed-in-user show --query id -o tsv`
   - Falls back to empty if service principal (CI)
   - Never prompt

8. **DEPLOY_RBAC**
   - Default to `true`
   - Never prompt

### Integration Changes

**azure.yaml** — preprovision hook order:
```yaml
preprovision:
  shell: sh
  run: |
    bash infra/scripts/collect-deployment-params.sh
    bash infra/scripts/select-model-regions.sh
    bash infra/scripts/setup-entra-app.sh
```

**setup-entra-app.sh** — now persists `ENTRA_CLIENT_ID` and `ENTRA_TENANT_ID` back to azd env after creating/finding the app (idempotent).

**README.md** — Manual Deployment section rewritten from 7 steps to 3 steps:
1. Clone and authenticate (`az login` + `azd auth login`)
2. Run `azd up` (all param collection happens automatically)
3. Verify

All manual `azd env set` cheatsheets removed. The parameter table removed. The "azd env new" step removed (azd up creates env automatically if needed).

## Benefits

- **First-run experience:** `azd up` just works — no manual parameter collection required
- **Idempotent:** Subsequent runs reuse saved params, no re-prompting
- **Auto-discovery:** 5 of 8 params are auto-discovered from Azure CLI, only 3 prompt
- **CI-friendly:** GitHub Actions can skip prompts, only auto-discover what's possible, fail fast on truly missing required vars
- **Consistent pattern:** Same `azd env get-value` + auto-discovery + persist pattern used across all preprovision scripts (region picker, param orchestrator)

## Auto-Discovery Sources

| Parameter | Auto-Discovery Source |
| --- | --- |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` (or list via `az account list` if multiple) |
| `AZURE_LOCATION` | `azd env get-value AZURE_LOCATION` (azd sets during `env new`) |
| `ENTRA_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `DEPLOYER_PRINCIPAL_ID` | `az ad signed-in-user show --query id -o tsv` |
| `DEPLOY_RBAC` | Default: `true` |

Optional params (`CUSTOM_DOMAIN_NAME`, `EXISTING_CERT_NAME`, `ENTRA_CLIENT_SECRET`) are prompted once in interactive mode, or default to empty in CI.

## Validation

- `bash -n infra/scripts/collect-deployment-params.sh` ✅
- `bash -n infra/scripts/setup-entra-app.sh` ✅
- `bash -n infra/scripts/select-model-regions.sh` ✅
- `python3 -c "import yaml; yaml.safe_load(open('azure.yaml'))"` ✅

## Future Use

This pattern applies to ANY azd preprovision parameter. For new parameters:
1. Add a `collect_<param>()` function in `collect-deployment-params.sh`
2. Check `azd env get-value <PARAM_NAME>` first (idempotent)
3. Try to auto-discover from Azure CLI if possible
4. Prompt only if interactive TTY (`! is_noninteractive`)
5. Persist via `azd env set <PARAM_NAME> <value>`

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
