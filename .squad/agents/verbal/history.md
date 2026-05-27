# Verbal — History

## Project Context
Turbo Voice Agent — Azure infrastructure and DevOps.
Stack: Bicep IaC, Azure Container Apps, ACI sandbox, GitHub Actions CI/CD, Docker.
User: the project maintainer.

Infrastructure: Azure Container Apps for backend + frontend, ACI for sandbox containers, Cosmos DB, Azure Storage for skills, ACR for container images. Deployed via `azd up`.

## Core Context

**Architecture Summary:**
- **Multi-region AI Foundry:** 3 separate Foundry accounts (Primary: gpt-5.2/4.1/4o-transcribe; Voice: gpt-realtime; Research: o3-deep-research)
- **Dynamic Sessions (2026-05-27 archived):** Azure Container Apps sessionPools replaced ACI sandbox; subsecond allocation verified in production
- **Deployment Pattern:** azd preprovision hooks for interactive region/param selection (idempotent, CI-safe)
- **Quota Strategy:** Per-model checking (OpenAI.GlobalStandard.<model-name>, not aggregate OpenAI.Standard)
- **Bicep Patterns:** RBAC must execute BEFORE app deployment (or use two-phase approach); Cosmos private networking complete (VNet, private endpoint, DNS zone, CAE VNet integration pending provider registration)
- **Stdout Discipline:** Command substitution functions route diagnostic output to stderr only; clean values to stdout for env var capture
- **GitHub Sandbox:** Header-based X-GH-Token on first session request per dev-task; skills sync precedes exec calls

**Known Blockers:**
- Container App RBAC timing: manual workaround applied (2026-05-22); permanent two-phase Bicep refactor pending in decisions.md
- CAE VNet integration: Microsoft.ContainerService provider registration blocked since 2025-07-29

**Key Scripts & Modules:**
- `infra/scripts/select-model-regions.sh` — quota-aware, interactive region picker (deployed 2026-05-20)
- `infra/scripts/collect-deployment-params.sh` — automated param collection for GitHub Actions
- Session pool Bicep module: `infra/modules/session-pool.bicep` (wired by Keaton 2026-05-22)
- Backend `SessionSandboxClient`: HTTP client for Azure dynamic sessions API (Fenster 2026-05-22)

For pre-2026-05 learnings and detailed troubleshooting, see git history (commits b70212d–e1e2a3d) and `infra/README.md` Troubleshooting section.

## Core Context — Recent Focus (2026-05)
- Quota-aware region selection for multi-region AI Foundry deployments (`select-model-regions.sh`)
- Automated deployment parameter collection (`collect-deployment-params.sh`)
- Deployment parameter orchestration & CI/CD workflow genericization
- Fixed stdout/stderr pollution bug in region picker causing env var persistence failure
- Fixed per-model quota dimension checking (OpenAI.GlobalStandard.<model-name> not generic OpenAI.Standard)
- Diagnosed & recovered Container App RBAC timing catch-22: identity created before ACR Pull role assignment

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

### 2025 Deployment Summary

**2025-01-23:** Deployed Fenster's local dev fallbacks (commit de81b4d): ACI sandbox init guards, PPTX MIME type support, PDF fallback to local storage, optimized ACI polling (2s intervals). Backend and frontend deployed to Azure via `azd deploy` with no issues.

**2025-07-25 to 2025-07-29:** Cosmos DB private networking deployment completed via Bicep IaC. Implemented VNet CAE (10.2.0.0/16), private endpoint with DNS zone (pe-cosmos-2mta7feoalzyq), bidirectional VNet peering (vnet-cae ↔ vnet-aci-sandbox), and disabled public access on Cosmos DB. All components verified: private endpoint approved, backend running, 9 Cosmos containers intact, VNet peering connected (both "Connected"). CAE VNet integration deferred due to Microsoft.ContainerService provider registration issue (not blocking current functionality). Artifacts: `.squad/orchestration-log/2026-03-29T1052-verbal-deploy.md`, all Bicep IaC in `infra/modules/`.

### Cosmos DB Private Networking Session (2026-03-29T10:52)

### OSS Infra Genericization (2026-05-19)
- `infra/main.parameters.json` now defaults optional OSS parameters to empty strings (`ENTRA_CLIENT_SECRET`, `CUSTOM_DOMAIN_NAME`, `EXISTING_CERT_NAME`, `DEPLOYER_PRINCIPAL_ID`) so `azd env set` can stay minimal for default deployments.
- `azure.yaml` now declares custom pipeline variables/secrets for GitHub Actions and documents the required `azd env set` names inline.
- `.github/workflows/deploy.yml` is OIDC-only and now reads deployer RBAC behavior from configuration instead of a hardcoded `false`; deploys are re-enabled for relevant path changes.
- `az bicep build --file infra/main.bicep` compiles successfully after the OSS parameterization changes (existing Bicep warnings remain in unrelated modules).
- Git history audit found one critical tracked key file (`backend/key.pem`, first committed in `4fdbe03`) and one suspicious tracked local env artifact (`frontend/.!38121!.env.local`, also `4fdbe03`).
- GUIDs still present in `infra/` are Azure built-in role definition IDs, not personal subscription, tenant, or principal identifiers.

### Quota-Aware Region Selection (2026-05-19)
**Problem:** `azd up` was failing for new users because hardcoded regions (eastus2/westus/centralus) lacked quota for OpenAI models on their subscriptions.

**Solution:** Added `infra/scripts/select-model-regions.sh` preprovision hook that:
- Queries Azure for model availability using `az cognitiveservices model list --location <region>`
- Checks quota using `az cognitiveservices usage list --location <region>` (parses JSON for OpenAI.Standard quota dimensions)
- For each of 3 Foundry accounts, finds regions where ALL models in that group are available AND have quota
- Interactively prompts user to pick a region (numbered list, with current default marked)
- Stores selections via `azd env set AZURE_OPENAI_LOCATION_PRIMARY/VOICE/RESEARCH`
- Idempotent: skips prompt if env vars already set
- Non-interactive guard: fails fast with clear error message if running in CI without pre-set env vars

**Model groups:**
- **Primary Foundry** (eastus2 default): gpt-5.2, gpt-4.1, gpt-4o-transcribe
- **Voice Foundry** (centralus default): gpt-realtime
- **Research Foundry** (westus default): o3-deep-research

**Infrastructure changes:**
- `infra/main.bicep`: added 3 new params (`primaryAiLocation`, `voiceAiLocation`, `researchAiLocation`), replaced hardcoded `location: 'eastus2'` / `'westus'` / `'centralus'` with param values
- `infra/main.parameters.json`: added 3 params with azd env var substitution (e.g., `${AZURE_OPENAI_LOCATION_PRIMARY=eastus2}`)
- `azure.yaml`: preprovision hook now runs `select-model-regions.sh` BEFORE `setup-entra-app.sh` (fail-fast on quota issues); added 3 new pipeline variables for GitHub Actions
- `README.md`: documented interactive region selection on first `azd up`, manual override for CI/non-interactive

**Validation:**
- `bash -n` script syntax check: ✅
- `az bicep build`: ✅ (pre-existing warnings unaffected)
- JSON validation: ✅
- YAML validation: ✅

**Detection approach:**
- Candidate regions: eastus, eastus2, westus, westus2, westus3, northcentralus, southcentralus, centralus, swedencentral, westeurope, francecentral, uksouth, japaneast, australiaeast
- Model availability: `az cognitiveservices model list` returns JSON array; if model name found, it's available
- Quota check: parse OpenAI.Standard usage (`currentValue` < `limit` = quota remaining)
- For multi-model groups (e.g., Primary = 3 models), only offer regions where ALL models are available

**Gotchas:**
- Some models (o3-deep-research, mistral-document-ai) only available in 2-3 regions worldwide — candidate list is intentionally broad
- Quota API returns OpenAI.Standard aggregate, not per-model granularity — conservative check (if ANY OpenAI.Standard has remaining quota, region is considered viable)
- If NO regions with quota, script prints manual override instructions and exits 1

### Deployment Parameter Orchestrator (2026-05-19)
**Problem:** README instructed users to manually `azd env new`, then `azd env set` six parameters by hand. Poor first-run experience.

**Solution:** Created `infra/scripts/collect-deployment-params.sh` preprovision hook that:
- Runs FIRST in preprovision (before region selection, before Entra setup)
- For each param: (1) check `azd env get-value`, (2) auto-discover from Azure CLI, (3) prompt if interactive, (4) persist via `azd env set`
- Fully idempotent — safe to run multiple times, only prompts once per param
- CI guard: no prompts in `GITHUB_ACTIONS=true`, only auto-discovery, fails fast with clear list of missing vars

**Parameters collected (in order):**
1. `AZURE_SUBSCRIPTION_ID` — auto-discover via `az account show --query id -o tsv`, or list subs and prompt if multiple available. Persist + `az account set`.
2. `AZURE_LOCATION` — used by azd for resource group. Check `azd env get-value` first (azd normally sets this); only prompt if truly empty.
3. `ENTRA_TENANT_ID` — auto-discover via `az account show --query tenantId -o tsv`. Never prompt.
4. `CUSTOM_DOMAIN_NAME` — optional. Prompt once: "Custom domain (leave empty to use Container Apps default):". Persist (empty string is valid).
5. `EXISTING_CERT_NAME` — optional. Only prompt if CUSTOM_DOMAIN_NAME is non-empty.
6. `ENTRA_CLIENT_SECRET` — optional. Prompt once with explanation ("Only needed for Microsoft To Do OAuth — press Enter to skip:"). Persist using `azd env set --secret` if available.
7. `DEPLOYER_PRINCIPAL_ID` — auto-discover via `az ad signed-in-user show --query id -o tsv`. Never prompt. Falls back to empty if service principal (CI).
8. `DEPLOY_RBAC` — default to `true`. Never prompt.

**Auto-discovery sources:**
- Subscription ID: `az account show --query id -o tsv` (or list via `az account list --query "[].{name:name,id:id}" -o tsv`)
- Tenant ID: `az account show --query tenantId -o tsv`
- Deployer principal ID: `az ad signed-in-user show --query id -o tsv`
- Location: `azd env get-value AZURE_LOCATION` (azd sets during `env new`)

**Integration changes:**
- `azure.yaml`: preprovision hook order is now: collect-deployment-params.sh → select-model-regions.sh → setup-entra-app.sh
- `setup-entra-app.sh`: now persists `ENTRA_CLIENT_ID` and `ENTRA_TENANT_ID` back to azd env after creating/finding the app (idempotent)
- `README.md`: Manual Deployment section rewritten from 7 steps (with explicit `azd env new` + 6 manual `azd env set` commands) to 3 steps: clone+auth, `azd up`, verify. All param collection happens automatically.

**Pattern:** Same `azd env get-value` + auto-discovery + persist pattern as the region picker. Reusable for ANY azd preprovision param.

### Quota Dimension Bug Fix (2026-05-20)
**Problem:** Region picker was passing `centralus` as having quota for `gpt-realtime`, but `azd up` preflight correctly failed with "Insufficient quota: Requested 10, Available 0". Root cause: `has_quota()` checked ANY `OpenAI.Standard.*` dimension (too coarse), but Azure uses exact per-model quota dimensions like `OpenAI.GlobalStandard.gpt-realtime`.

**Fix:** Completely rewrote quota checking in `select-model-regions.sh`:
- Replaced `has_quota()` with `has_quota_for_model(region, model, required_capacity)` — checks EXACT quota dimension `OpenAI.GlobalStandard.<model-name>`
- Added parallel capacity arrays: `PRIMARY_CAPACITY=(500 500 200)`, `VOICE_CAPACITY=(10)`, `RESEARCH_CAPACITY=(1500)` to match model arrays
- `find_available_regions()` now checks EVERY model in a group against its required capacity — region passes iff ALL models have sufficient quota
- Added `get_quota_info()` for verbose output — prints per-region per-model availability + quota like "✓ gpt-realtime — quota 10/10 available (need 10)"
- Tightened `is_model_available()` to also check quota dimension exists (even if exhausted), catching model-actually-not-in-region
- Added env var validation on each run: if `AZURE_OPENAI_LOCATION_VOICE` (or other) no longer has quota for its models, auto-clear and re-prompt with warning
- Verbose output by default (interactive users want feedback during 30-60s region scan)

**Quota dimension naming discovered:**
- Format: `OpenAI.<SKU>.<model-name>` exactly
- SKU is `GlobalStandard` for all current models (gpt-5.2, gpt-4.1, gpt-4o-transcribe, gpt-realtime, o3-deep-research)
- Each model has its own independent quota pool
- Query: `az cognitiveservices usage list --location <r> --query "[?name.value=='OpenAI.GlobalStandard.<model>']"`

**Pascal action required:** Your azd env's `AZURE_OPENAI_LOCATION_VOICE=centralus` will be auto-detected as invalid on next `azd up` and you'll be re-prompted to select a region with quota.

**Validation:**
- `bash -n` syntax check: ✅
- Dry-run query (eastus2 for gpt-realtime): ✅ confirmed schema matches parser
- Per-model quota arrays match bicep capacity values: ✅ (eastus2: 500/500/200, centralus: 10, westus: 1500)

### Region Picker Stdout Pollution Fix (2026-05-20)
**Problem:** `select-model-regions.sh` never persisted the selected regions to azd env vars. `.azure/turbo-voice/.env` showed `collect-deployment-params.sh` worked fine, but `AZURE_OPENAI_LOCATION_PRIMARY/VOICE/RESEARCH` were missing. Bicep fell back to hardcoded centralus for voice → quota warning.

**Root cause — TWO bugs:**
1. **Stdout pollution in command substitution:** `find_available_regions()` and `pick_region()` both write diagnostic output (region scan progress, numbered menus, selection confirmations) to stdout. These get captured by `$(...)` substitution, making the captured value multiline garbage instead of clean region name. `azd env set` with garbage likely failed silently, and azd proceeded to provision with no env var set.
2. **Nameref (`local -n`) compatibility:** bash 3.2 (macOS default) doesn't support namerefs; even bash 5 via Homebrew had fragility here.

**Fixes applied:**
- **All diagnostic output → stderr:** Every `echo` in `find_available_regions()` and `pick_region()` now uses `>&2` except the final region output (space-separated list / single region). Only the return value goes to stdout for clean `$(...)` capture.
- **Interactive read from `/dev/tty`:** `read -rp ... </dev/tty` ensures prompts work even when stdin is piped under azd hook execution.
- **Replaced all `local -n` namerefs with indirect expansion:** `eval "local regions=(\"\${${regions_var}[@]}\"))"` for bash 3.2+ compatibility.
- **Removed empty-string `azd env set` calls:** Lines 352, 367, 382 deleted — setting empty doesn't unset and trips re-prompt path anyway. Just clear the local var.
- **Added ERR trap:** `trap 'echo "❌ select-model-regions.sh failed at line $LINENO (exit $?)" >&2' ERR` right after `set -euo pipefail` for debuggability.
- **Explicit `azd env set` verification:** Each `azd env set` call wrapped with `if ! azd env set ... ; then echo "❌ Failed..." >&2; exit 1; fi` for three critical vars.
- **Final round-trip verification:** After setting all 3 vars, `main()` now does `azd env get-value` for each and exits 1 if any mismatch. Proves persistence worked.
- **All stdout in `main()` → stderr:** Even the banner and subscription check output now use `>&2` to avoid polluting any future command substitution uses.

**Pascal action:** No state to clear — the env vars were never written. Just re-run `azd up`. The picker will now run correctly, show you the region menus, and persist the values.

**Validation:**
- `bash -n` syntax check: ✅
- Stdout/stderr discipline: manual code inspection confirms all diagnostic output now uses `>&2`
- Portability: no bash 4.x-only features remain

### Container App RBAC Timing Issue (2026-05-22)

**Problem:** `azd up` failed with "Operation expired" during Container App provisioning.

**Root cause:** Bicep module dependency ordering catch-22:
- Container App needs ACR Pull role to pull placeholder image
- RBAC module depends on `backend.outputs.principalId`
- If backend fails, RBAC module never executes
- Backend failed because ACR auth returned 401 (no RBAC yet)

**Evidence:**
- System logs: 88 repeated "ACR token exchange endpoint returned error status: 401"
- Backend identity had ZERO role assignments (RBAC module never ran)
- Container App in "Failed" state with no revisions created
- ACR repository completely empty (no images pushed — provision failed before deploy)

**Manual recovery applied (2026-05-22 07:08:14 UTC):**
```bash
az role assignment create \
  --assignee <backend-principal-id> \
  --role "7f951dda-4ed3-4680-a7ca-43fe172d538d" \
  --scope "<acr-resource-id>"
```

**Pattern:** Container Apps with system-assigned identities need ACR Pull role IMMEDIATELY after identity creation, not in a dependent module. Consider two-phase RBAC:
1. Phase 1: ACR Pull only (inline or separate lightweight module with no health dependencies)
2. Phase 2: All other permissions (Cosmos, Storage, AI Foundry) after app is healthy

**Next steps for user:**
1. Run `azd provision` to complete infrastructure setup (RBAC now exists)
2. Run `azd deploy` to build and push container images
3. Implement two-phase RBAC Bicep refactor (see `.squad/decisions/inbox/verbal-aca-rbac-timing-fix.md`)

**Files involved:**
- `infra/modules/rbac.bicep` (lines 144-152: ACR Pull assignments)
- `infra/main.bicep` (line 330: RBAC module invocation)
- `infra/modules/container-app-backend.bicep` (line 109: placeholder image)

### Container App RBAC Timing Issue — Second Occurrence (2026-05-22 08:44 UTC)

**Problem:** After manually fixing backend identity and running `azd provision`, frontend and sandbox Container Apps failed with identical RBAC issue.

**Evidence — SECOND OCCURRENCE:**
- Backend succeeded (manual RBAC fix from previous session worked)
- Frontend failed: "ContainerAppOperationError: Failed to provision revision for container app 'ca-frontend-2mta7feoalzyq'. Error details: Operation expired."
- Sandbox failed: "ContainerAppOperationError: Failed to provision revision for container app 'ca-sandbox-2mta7feoalzyq'. Error details: Operation expired."
- Both frontend (6216b79f-7f75-4697-87de-6374f03bd4d9) and sandbox (92e01376-0bc6-46ef-aeda-2fbc13dcd46a) identities had ZERO role assignments
- `azd deploy` subsequently failed: "could not determine container registry endpoint, ensure 'registry' has been set in the docker options or 'AZURE_CONTAINER_REGISTRY_ENDPOINT' environment variable has been set"
- Azd env was missing ALL Bicep outputs (AZURE_CONTAINER_REGISTRY_ENDPOINT, BACKEND_URL, FRONTEND_URL, COSMOS_ENDPOINT, AI_*_ENDPOINT, SANDBOX_URL) because provision failed mid-way

**Root cause confirmed:**
- All three Container Apps (backend, frontend, sandbox) have `registries` blocks that reference ACR with `identity: 'system'`
- Backend and frontend use UNCONDITIONAL registries blocks; sandbox uses conditional `!empty(acrLoginServer) ? [...] : []`
- Even though placeholder image is public (`mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`), presence of `registries` block causes Azure to attempt ACR authentication
- Without AcrPull role, authentication fails with 401, Container App provision times out after 20 minutes
- RBAC module depends on Container App outputs, so it never runs → no role assignments created
- Bicep outputs never populate azd env because provision fails mid-deployment

**Manual recovery applied (2026-05-22 08:44 UTC):**
```bash
# Frontend AcrPull grant
az role assignment create --assignee 6216b79f-7f75-4697-87de-6374f03bd4d9 \
  --role 7f951dda-4ed3-4680-a7ca-43fe172d538d \
  --scope /subscriptions/2883501d-be4e-457b-9377-4867fb27b394/resourceGroups/rg-turbo-voice-agent/providers/Microsoft.ContainerRegistry/registries/acr2mta7feoalzyq

# Sandbox AcrPull grant
az role assignment create --assignee 92e01376-0bc6-46ef-aeda-2fbc13dcd46a \
  --role 7f951dda-4ed3-4680-a7ca-43fe172d538d \
  --scope /subscriptions/2883501d-be4e-457b-9377-4867fb27b394/resourceGroups/rg-turbo-voice-agent/providers/Microsoft.ContainerRegistry/registries/acr2mta7feoalzyq

# Manual env var fix (should be populated by Bicep outputs)
azd env set AZURE_CONTAINER_REGISTRY_ENDPOINT acr2mta7feoalzyq.azurecr.io
```

**Sandbox image strategy:**
- Bicep creates Container App with public placeholder image `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`
- `azd deploy` builds and pushes sandbox image with timestamped tag: `turbo-voice-agent/sandbox-{envName}:azd-deploy-{ts}`
- Postdeploy hook (`infra/scripts/tag-sandbox-latest.sh`) tags latest sandbox image as `turbo-voice-agent/sandbox:latest` via `az acr import`
- ACI container groups pull from `:latest` tag for predictable reference

**Pattern confirmation:**
This is the SECOND independent occurrence of the exact same failure mode, validating the diagnosis. The two-phase RBAC Bicep refactor (`.squad/decisions.md` lines 20-76) is now URGENT — must be implemented before next full `azd down && azd up` cycle.

**Next steps for user:**
1. `azd provision` — should succeed now that RBAC is fixed for all three apps
2. `azd deploy` — will build & push images, populate remaining azd env vars via postprovision hook
3. Implement two-phase RBAC Bicep refactor (decision already documented, just needs execution)

### Container App RBAC Collision — Manual Fix Side Effect (2026-05-22 09:15 UTC)

**Problem:** After manually fixing RBAC in previous two sessions, `azd provision` failed with "RoleAssignmentExists" errors on all three Container Apps.

**Root cause:** Manual `az role assignment create` uses RANDOM GUIDs for role assignment names (Azure CLI default). Bicep `rbac.bicep` module uses DETERMINISTIC names via `guid(scope, principalId, roleDefId)`. Azure RBAC enforces uniqueness on (principal, role, scope) triple — so Bicep's attempt to create an assignment with its deterministic name fails because an assignment for the same triple ALREADY exists under a different name (the random GUID from manual fix).

**Error details:**
```
RoleAssignmentExists: The role assignment already exists. The ID of the existing role assignment is adfdc86b110c47f09986e14888ff879b.
RoleAssignmentExists: The role assignment already exists. The ID of the existing role assignment is 4e7e6a5b54384a649b8ffbd38d63927e.
RoleAssignmentExists: The role assignment already exists. The ID of the existing role assignment is 7b86777c10a04b3bbce5b947b2255375.
```

**Evidence:** Listed ACR AcrPull role assignments:
- `adfdc86b-110c-47f0-9986-e14888ff879b` → backend (principal e8b91c28-9125-4f2f-a64a-8a536fc8e66e)
- `4e7e6a5b-5438-4a64-9b8f-fbd38d63927e` → frontend (principal 6216b79f-7f75-4697-87de-6374f03bd4d9)
- `7b86777c-10a0-4b3b-bce5-b947b2255375` → sandbox (principal 92e01376-0bc6-46ef-aeda-2fbc13dcd46a)
- 1 additional assignment (ade2c0be... for principal 777b2d79...) NOT in error message — likely a successfully deployed Bicep assignment

**Recovery applied (2026-05-22 09:15 UTC):**
```bash
# Delete the three manual role assignments by their IDs
az role assignment delete --ids \
  /subscriptions/2883501d-be4e-457b-9377-4867fb27b394/resourceGroups/rg-turbo-voice-agent/providers/Microsoft.ContainerRegistry/registries/acr2mta7feoalzyq/providers/Microsoft.Authorization/roleAssignments/adfdc86b-110c-47f0-9986-e14888ff879b \
  /subscriptions/2883501d-be4e-457b-9377-4867fb27b394/resourceGroups/rg-turbo-voice-agent/providers/Microsoft.ContainerRegistry/registries/acr2mta7feoalzyq/providers/Microsoft.Authorization/roleAssignments/4e7e6a5b-5438-4a64-9b8f-fbd38d63927e \
  /subscriptions/2883501d-be4e-457b-9377-4867fb27b394/resourceGroups/rg-turbo-voice-agent/providers/Microsoft.ContainerRegistry/registries/acr2mta7feoalzyq/providers/Microsoft.Authorization/roleAssignments/7b86777c-10a0-4b3b-bce5-b947b2255375
```

**Post-deletion state:**
- Only 1 AcrPull assignment remains on ACR (the 4th assignment not involved in the collision)
- All three Container Apps remain "Succeeded" provisioning state with running revisions
- ⚠️ Container Apps temporarily have NO ACR Pull access until `azd provision` recreates assignments with deterministic names

**Critical learning:** Manual `az role assignment create` will COLLIDE with subsequent Bicep deployments if Bicep uses deterministic GUID naming. Two solutions:
1. **Preferred for manual fixes:** Always specify `--name` with deterministic GUID: `--name "$(az rest --method POST --uri 'https://management.azure.com/subscriptions/{sub}/providers/Microsoft.Resources/calculateTemplateHash?api-version=2020-06-01' --body "{'template': '{\"scope\":\"<scope>\",\"principalId\":\"<principal>\",\"roleDefId\":\"<role>\"}'}' --query hash -o tsv)"`
2. **Simpler for recovery:** Delete manual assignments before re-running `azd provision` (Bicep recreates them with correct names)

**Skill update:** Added "Side effects" warning to `.squad/skills/aca-provision-recovery/SKILL.md` documenting this collision pattern.

**Next steps for user:**
1. `azd provision` — Bicep recreates the three AcrPull assignments with deterministic names (plus any other RBAC: Cosmos, Storage, AI Foundry)
2. `azd deploy` — builds and pushes actual application images
3. Implement two-phase RBAC Bicep refactor (URGENT — failure cycle repeats on next `azd down → azd up`)

## Learnings — 2026-05-22 (sandbox-dynamic-sessions Phase 1)

**Work:** Landed Phase 1 session pool infra (tasks 1.1–1.8). New `infra/modules/session-pool.bicep` + `session-pool-role.bicep`. Deleted ACI + sandbox CA modules. Phase 1 was partially pre-landed in `bcdb0bf` (Fenster's Phase 2 commit) with 3 latent Bicep schema bugs: `cooldownPeriodInSeconds` placement, invalid `executionType`, wrong registry credential field name. Fixed and committed as `b70212d`. `az bicep build` clean.

**Catch-22 prevention pattern (now codified):**
1. **Deterministic role assignment names.** Every `Microsoft.Authorization/roleAssignments` uses `name: guid(scope, principalId, roleDefinitionId)` — idempotent across re-deploys, no manual `az role assignment create` workarounds. Applies to pool AcrPull AND backend→pool Session Executor.
2. **Real images, not placeholders.** The session pool starts from the real ACR sandbox image tag (`sandboxImageTag=latest`), not a hello-world placeholder that would 401-loop the way the deleted sandbox CA did.
3. **Break module cycles via computed FQDNs.** When module A needs module B's URL and B needs A's outputs, compute the FQDN deterministically (`ca-{name}-{token}.{cae.defaultDomain}` or `customDomainName` if set) rather than referencing `.outputs.fqdn`. Avoids `BCP080`.

Cross-references: `.squad/skills/aca-provision-recovery/SKILL.md`, decisions.md entry "Fix Container App RBAC Dependency Ordering".

## Learnings

### 2026-05 — Sandbox container readiness for Container Apps session pools (Phase 5)

**Probe split pattern (Liveness vs Startup):**
- `/health`: cheap liveness, returns 200 the instant Node is listening. No I/O. Used by pool's Liveness probe on 10s period during steady state.
- `/ready`: startup gate, returns 503 until skill sync completes. Pool's Startup probe polls 5s × 30 attempts → 150s max. Once green, traffic is routed.
- Implementation: marker file `/tmp/sandbox-state/skills-synced` written by entrypoint.sh AFTER `sync-skills.sh` runs. `/ready` does `fs.existsSync` check (fast, no race).
- Even when Blob Storage is unreachable, write the marker anyway so the pool doesn't stall — graceful degradation per spec.

**X-GH-Token header → gh auth pattern:**
- Express middleware reads `req.get("X-GH-Token")`, pipes via stdin to `gh auth login --with-token`.
- Idempotency: in-process `ghAuthenticated` boolean + `ghAuthInFlight` Promise prevents concurrent first-request races (multiple first requests share one auth attempt).
- Token hygiene: never log the value; `delete req.headers["x-gh-token"]` after middleware to prevent leak into downstream proxy/child-process env.
- On auth failure: log stderr (token-free), reset `ghAuthInFlight` to null so a subsequent valid token can retry. Request still serves — many endpoints don't need gh.
- Token piped via spawn stdin, not shell — avoids ever materialising the token in argv or shell history.

**Smoke-test workaround when Docker daemon is unavailable:**
- `node --check server.js` catches syntax errors fast.
- Run `PORT=3099 node server.js` directly with deps installed — exercises express routes and middleware without container. Validated all four scenarios (health/ready-before/ready-after/header-fires).
- `docker info` returning non-zero is the signal that Docker daemon is down even if `docker` binary exists (e.g., on macOS without Docker Desktop running).

## 2026-05-22 — Phase 7 prep (sandbox-dynamic-sessions)

**Done:**
- Removed `sandbox` service from `azure.yaml` (no Container App exists post-Phase-1; `host: containerapp` was causing 20-min hangs).
- Created `infra/scripts/build-sandbox-image.sh` — `az acr build` directly to `turbo-voice-agent/sandbox:latest`, called from `postprovision` + `postdeploy` hooks. Replaces `tag-sandbox-latest.sh` (deleted).
- Created `scripts/cleanup-aci-orphans.sh` — idempotent safety net for users upgrading from ACI-era deployments. Reads RG from `azd env get-values`, supports `--yes` for CI.
- Created `infra/README.md` with upgrade notes pointing at the cleanup script.
- `az bicep build` clean.
- Checked off 7.1 + 7.2 in tasks.md; flagged 7.3 + 7.4 as awaiting Phase 4 + 6 (validation wave).

**Pattern reinforced:** sandbox image tag must stay synced between Bicep (`main.bicep:263`) and the build script. Both now reference `turbo-voice-agent/sandbox:latest`. If the Bicep param `sandboxImageTag` changes from `latest`, `build-sandbox-image.sh` must follow.

## Learnings — 2026-05-22 — Session pool ACR Pull chicken-and-egg
- `Microsoft.App/sessionPools` with `identity.type: SystemAssigned` + inline AcrPull role assignment is a deployment race that always loses on first deploy. The pool pulls during create; the role assignment runs after the pool's principalId resolves; the pool fails before the assignment can be applied.
- Symptom: `SessionPoolOperationError: pool group create/update failed with error: time out` in the deployment operation list. Outer azd surface looks like "resource with this name already exists or is in a conflicting state" because azd internally retries and the prior Failed pool is still there.
- Fix: **user-assigned MI** for the pool. Grant AcrPull on the registry in a separate module that runs BEFORE the pool module. `registryCredentials.identity` takes the UAMI resource ID directly.
- The session pool is in the CAE's region (East US 2 in this deployment), even though `AZURE_LOCATION=westeurope`. That's because `cae.outputs.id` is the source of truth — pool MUST match CAE region. Don't try to "fix" this.
- Pool delete via `az resource delete --ids <pool-id>` works (takes ~1 minute). No special `az containerapp sessionpool` CLI needed.
- Apply the same pattern (pre-granted UAMI for image pull) to **any future** ACA resource that creates+pulls in a single ARM operation. Container Apps themselves get away with system-assigned because their revision provisioning is async and ARM marks them Succeeded before the first pull completes — session pools do NOT have that grace.

## 2026-05-22T15:30Z — Session pool "pods crashing, count: 0" → stale ACR image

**Symptom after UAMI fix (`efd6565`) landed:** `azd provision` still failed at the pool with `SessionPoolOperationError: pool group create/update failed with error: pool is in bad status because pods are crashing, crashing pods count: 0`. Pool ended in `provisioningState: Failed`, `nodeCount: 0`, but UAMI was correctly attached and had AcrPull (so the previous variant was genuinely resolved).

**Smoking gun:**
- `az acr repository show -n acr2mta7feoalzyq --image turbo-voice-agent/sandbox:latest --query createdTime` → `2026-05-22T11:17:08Z`.
- `git log -1 --pretty=format:"%ad" --date=iso-strict ceae508 -- sandbox/` (Phase 5 `/health` + `/ready` + marker) → `2026-05-22T11:43:04Z`.
- Image is **26 minutes older than the Phase 5 commit**. The pool's Liveness probe (`/health`, 10s) and Startup probe (`/ready`, 5s × 30) were hitting endpoints that don't exist in the running container. Pods get 404, Liveness kills them within ~30s, pool reports "crashing" with `nodeCount: 0`.

**Why the image was stale:** `build-sandbox-image.sh` was wired only to `postprovision` + `postdeploy`. Each `azd provision` died at the pool step → post-hooks never ran → `:latest` stayed at the pre-Phase-5 digest forever. Chicken-and-egg: pool fails because image is stale, image won't rebuild because pool fails.

**"crashing pods count: 0" semantics:** this RP message does NOT mean "zero failures". It means "currently zero healthy pods and the RP has given up". Pods are getting killed by Liveness before they ever reach the "running, then crashed" state the counter increments on.

**Fix shape (no code/Bicep change):**
1. `bash infra/scripts/build-sandbox-image.sh` — rebuilt directly in ACR (5m 18s via `az acr build`). New digest `sha256:7ec04eaa664a0f91a478071680dad4df1ef5462401ae94319c00807b9460aa92`.
2. `az resource delete --ids .../sessionPools/sp-sandbox-2mta7feoalzyq` — clears the Failed resource so retry isn't blocked by name collision (~3m).
3. `azure.yaml` — added `bash infra/scripts/build-sandbox-image.sh` to the `preprovision` hook (Posix + Windows branches). The script already exits 0 cleanly when `AZURE_CONTAINER_REGISTRY` is unset (first-ever run), so it is safe to add unconditionally. Eliminates the staleness window for every future run.

**Validation:** `python3 -c "import yaml; yaml.safe_load(open('azure.yaml'))"` OK. `az bicep build` clean (only pre-existing warnings). Pool is deleted, fresh image is in ACR.

**Pascal's next step:** `azd provision`. Preprovision will rebuild the image again (no-op-equivalent since source is unchanged from the manual rebuild), pool will be created, will pull `:latest`, probes will return 200, `nodeCount` will climb to `readySessionInstances=1`, deployment will succeed, postprovision/postdeploy fire and refresh outputs.

**Patterns reinforced:**
- Any deployment where the image-build hook only runs *after* successful resource create is latently vulnerable to this loop if the resource pulls the image and probes app-level endpoints. Mitigation: ensure at least one image-build invocation runs *before* the resource is reconciled.
- "Pool in bad status, crashing pods count: 0" is a structural message — read it as "no healthy pods, RP gave up". Treat as application-side failure (probe / startup / image), not pool-config failure.
- Image freshness diagnostic: `az acr repository show ... --query createdTime` vs `git log -1 --pretty=format:"%ad" --date=iso-strict -- <source-dir>`. If image is older than the source dir, you have a postprovision-hook chicken-and-egg.

**Skill updated:** `.squad/skills/aca-provision-recovery/SKILL.md` gained section "Session Pool Variant: Stale Image Probe Mismatch (Postprovision Chicken-and-Egg)".

## 2026-05-22 — Sandbox POST /tasks 400 after Phase 5 (X-GH-Token migration)
**Requested by:** Pascal van der Heiden

**Symptom:** Session pool allocates fast (UAMI pre-grant is working). First `POST /tasks` from `dev_agent._sandbox_exec` returns 400 "GitHub token required". Terminal also showed "No skills available in sandbox." — that's informational (blob `skills` container is empty), not the failure.

**Root cause (one line):** Phase 5 added an `X-GH-Token` request middleware that runs `gh auth login --with-token` and sets `ghAuthenticated = true`, but the `POST /tasks` validation gate (L179 in `sandbox/server.js`) still required `effectiveToken = req.body.ghToken || process.env.GH_TOKEN`. In session pools neither is set — the token only arrives via header. **Stale validation gate.**

**Fix (`sandbox/server.js`, one line):**
```diff
- if (prompt && !effectiveToken) { return res.status(400)... }
+ if (prompt && !effectiveToken && !ghAuthenticated) { return res.status(400)... }
```
The spawned `copilot` CLI reads from `gh` auth state — no `GH_TOKEN` env var needed. Existing L204 conditional env injection already handles the no-env-var path correctly.

**Image rebuild:** `bash infra/scripts/build-sandbox-image.sh` → `az acr build`, server-side, ~3 min. Pool picks it up on next allocation; existing prewarmed instances may serve stale until pool cooldown — Pascal can force-recycle via `az resource delete` on the pool if he doesn't want to wait.

**What I deliberately did NOT change:**
- `entrypoint.sh` startup sync — already correct (unconditional marker write so `/ready` doesn't stall on empty/unreachable storage).
- `sync-skills.sh` — works as designed. Empty `skills` blob container is a data state, not a bug.
- `POST /skills/sync` lazy endpoint — already implemented and wired in `dev_agent._sync_skills_stage`. The "proper" per-task architecture Pascal hypothesised is already in place.
- Backend payload (`dev_agent._sandbox_exec` L1359–1413) — sends `X-GH-Token` as a header on first call per task. That IS the Phase 5 design.

**Skill updated:** `aca-provision-recovery/SKILL.md` gained section "Session Pool Variant: Per-Task Config vs Container-Startup Config" — generic pattern for the class of bug that happens when migrating per-user containers to shared session pools. Includes a diagnosis checklist (audit every `status(40x)` gate, map config sources to docker-compose-era vs pool-era paths, look for mismatches).

**Learnings:**
- When migrating per-user → shared-pool, every input the container accepted at startup (env vars, mounted secrets) must be re-classified as column-1 (still OK at startup) or column-2 (must move to per-task delivery). Route handlers must accept column-2 as a valid alternative to column-1, not as a mutually exclusive replacement.
- "No skills available" UX message is benign here — the blob container being empty is correct early-stage behaviour. Not worth changing the wording unless users find it alarming. Flag for Pinback if it ever lands on a UX backlog.
- Did NOT run `az monitor log-analytics query` for this one — the bug was unambiguously reproducible from reading the code against the known backend payload. Logs would have confirmed only what the source already proved. Saving the runbook for non-obvious cases.

---

## Skills blob container seeding (gap from sandbox-dynamic-sessions)

**Date:** 2025
**Trigger:** Pascal reported `/skills/sync` returning `synced: 0, skills: []` after deploy. Container was empty.

**Root cause:** The `sandbox-dynamic-sessions` change wired up the *consumer* side (sandbox entrypoint downloads from `skills` blob container at warm-up) but not the *producer* side at deploy time. The OpenSpec design glossed over it ("skills are already in the blob, identical to ACI behavior") but the original ACI flow never had a deploy-time upload either — every prior environment was running on whatever skills users had activated via the marketplace (`CosmosSkillsService.upload_skill_from_github_to_blob`). Platform-bundled skills in `.github/skills/` had no upload path.

**Fix:**
- New `infra/scripts/upload-skills.sh` — uploads `.github/skills/` → `skills` container via `az storage blob upload-batch --auth-mode login`. Idempotent.
- Added `AZURE_STORAGE_ACCOUNT_NAME` Bicep output → propagates to azd env automatically.
- Wired into `azure.yaml` `postprovision` (posix + windows).
- Verified live against `st2mta7feoalzyq`: 20 blobs across 6 skills uploaded successfully.

**Network ACL gotcha:** Storage account has `networkAcls.defaultAction = 'Deny'` (correct for production). The script handles this by temporarily adding the caller's public IP, waiting **60s** for ACL propagation (20s is too short — confirmed empirically), then removing the rule in a trap on exit. Requires deployer RBAC: `Storage Blob Data Contributor` AND `Storage Account Contributor`.

**Learnings:**
- When migrating from "container = per-user/per-task" to "container = shared infrastructure," every artifact that used to live IN the container (or in a per-user volume) must be reclassified as either:
  - **(a) Bundled in the image** — ships with every deploy, requires image rebuild to update.
  - **(b) Uploaded to shared storage at deploy time** — ships with every deploy via IaC hooks, updates without image rebuild.
  - **(c) Uploaded at runtime by users/backend** — already covered by per-user activation flow.
- The blob container being declared in Bicep does NOT seed it. Bicep only creates the *container resource*, never its data plane contents. Easy thing to miss when the consumer code "just works" against an empty container without crashing.
- Azure Storage ACL propagation: 20s insufficient, 60s reliable. Adjust scripts accordingly.
- `--auth-mode login` for blob uploads is much cleaner than juggling keys — but requires the deployer to have data-plane RBAC, not just control-plane.

## 2026-05-26: Azure Validation Runbook + Skills-Sync Investigation Flagged

**Task:** Produce Azure validation runbook for Pascal to debug sandbox pool startup failures (commit `909418a`).

**Delivered:** `.squad/decisions/inbox/verbal-azure-validation-runbook.md` — 381 lines, 6 phases with auto-resolved resource names, copy-pasteable commands.

**Phases:**
- A.1: Pre-flight (backend revisions, pool status, image staleness)
- A.2: Pool refresh options
- A.2.2: Backend deploy
- A.3: Trigger controlled failures
- A.4: Capture logs
- B: Triage template

**Key finding noted:** `/skills/sync` returns 200 with `synced: 0` when blob storage not mounted or RBAC missing. Backend renders this as "No skills available in sandbox" (informational, not a failure). Fenster's diagnosis confirms blob container is currently empty (no user uploads yet).

**Investigation flagged for Verbal:** Verify session-pool container has `AZURE_STORAGE_ACCOUNT_NAME` set and MSI has Storage Blob Data Reader on the storage account. If both OK but sync still returns 0, blade issue (blob container truly empty) or `sync-skills.sh` error (log it, don't swallow).

**Next:** Await Pascal to execute runbook Phase A.1–A.4 and provide triage output.

## 2026-05-27: Sandbox Dynamic Sessions Archived

**Context:** Redfoot archived `sandbox-dynamic-sessions` OpenSpec change after full implementation verification and production deployment. Session pool live with subsecond allocation confirmed. See `.squad/decisions/decisions.md` for full decision.
