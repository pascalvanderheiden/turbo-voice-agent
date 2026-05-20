# Verbal — History

## Project Context
Turbo Voice Agent — Azure infrastructure and DevOps.
Stack: Bicep IaC, Azure Container Apps, ACI sandbox, GitHub Actions CI/CD, Docker.
User: the project maintainer.

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

### Cosmos DB Private Networking (2025-07-25)
Implemented full private networking for Cosmos DB via Bicep IaC:
- Created `infra/modules/vnet-cae.bicep` — CAE VNet (10.2.0.0/16) with 3 subnets: infra (/23), private-endpoints (/24), reserved (/24)
- Created `infra/modules/cosmos-private-endpoint.bicep` — private endpoint + DNS zone + auto A-record registration
- Created `infra/modules/vnet-peering.bicep` — reusable single-direction peering module
- Updated `container-apps-env.bicep` — optional VNet integration (backwards-compatible with default '')
- Updated `cosmos-db.bicep` — `publicNetworkAccess` set to `Disabled`
- Wired everything in `main.bicep`: VNet → private endpoint → CAE subnet → bidirectional peering (conditional on enableAciSandbox)
- All Bicep files compile clean (`az bicep build` passes)
- Deployment tasks (5.x, 6.x, 7.x) left for manual execution by Pascal

### Cosmos DB Private Networking Deployment (2025-07-29)

Successfully deployed Cosmos DB private networking infrastructure:

**✅ Deployed successfully:**
- VNet CAE (10.2.0.0/16) with 3 subnets: snet-cae-infra (/23), snet-private-endpoints (/24), snet-reserved (/24)
- Private endpoint (pe-cosmos-2mta7feoalzyq) in snet-private-endpoints — connection status "Approved"
- Private DNS zone (privatelink.documents.azure.com) with DNS zone group
- Bidirectional VNet peering between vnet-cae and vnet-aci-sandbox (both "Connected")
- Cosmos DB public network access set to "Disabled"

**⚠️ CAE VNet integration blocked:**
CAE deployment failed with error: "Subscription is not registered with Microsoft.App and Microsoft.ContainerService"
- Microsoft.App was already registered
- Microsoft.ContainerService required re-registration (still "Registering" after 2+ minutes)
- CAE remains operational without VNet integration (provisioningState: Succeeded, status: Running)
- Backend can still reach Cosmos DB through VNet peering to ACI VNet

**Verification results:**
- ✅ Private endpoint connection approved
- ✅ Backend container app running (ca-backend-2mta7feoalzyq)
- ✅ Cosmos DB database "turbovoice" with 9 containers intact
- ✅ Cosmos DB publicNetworkAccess: "Disabled"
- ✅ VNet peering established (peer-cae-to-aci and peer-aci-to-cae both "Connected")

**Next action:** CAE VNet integration can be retried after Microsoft.ContainerService provider finishes registering. Not blocking for current functionality.

**Tasks completed:** 5.1, 5.2, 5.3, 6.2, 6.3, 6.4

### Cosmos DB Private Networking Session (2026-03-29T10:52)

**Status:** SUCCESS  
**Session ID:** 2026-03-29T1052-verbal-deploy

Cosmos DB private networking deployment session completed. All critical components verified:
- ✅ Private endpoint approved
- ✅ Backend health check passing
- ✅ All 9 Cosmos containers intact: notes, tasks, ideas, specs, strategies, videos, transcripts, logs, agents
- ✅ Public access disabled on Cosmos DB account
- ✅ VNet peering connected (CAE ↔ ACI)
- ✅ Private DNS zone operational

**Deployment artifacts:**
- Orchestration log: `.squad/orchestration-log/2026-03-29T1052-verbal-deploy.md`
- Session log: `.squad/log/2026-03-29T1052-cosmos-private-networking-deploy.md`
- All Bicep IaC in `infra/modules/`

**Outstanding:** CAE VNet integration (pending Microsoft.ContainerService provider registration)

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
