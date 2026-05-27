# Squad Decisions

# Decision: Fix Container App RBAC Dependency Ordering

---
date: 2026-05-22
author: verbal
status: URGENT
confidence: HIGH (confirmed by two independent occurrences)
---

## Problem
`azd up` failed during provision with "Operation expired" error. Root cause: Bicep dependency ordering issue.

**Failure sequence:**
1. Backend Container App created with system-assigned identity
2. Container App tries to pull placeholder image from ACR
3. ACR authentication fails (401) because RBAC module hasn't run yet
4. RBAC module depends on `backend.outputs.principalId`, but backend is in failed state
5. Deployment fails before RBAC can execute — catch-22

**Evidence (First Occurrence — 2026-05-22 07:08 UTC):**
- 88 repeated ACR auth errors: "ACR token exchange endpoint returned error status: 401"
- Backend identity (e8b91c28-9125-4f2f-a64a-8a536fc8e66e) had ZERO role assignments
- RBAC module never deployed (no deployment named 'rbac' found)

**Evidence (Second Occurrence — 2026-05-22 08:44 UTC):**
- After manually fixing backend RBAC, user ran `azd provision` again
- Backend succeeded (validated manual fix), but frontend and sandbox failed identically
- Frontend identity (6216b79f-7f75-4697-87de-6374f03bd4d9): ZERO role assignments → Operation expired
- Sandbox identity (92e01376-0bc6-46ef-aeda-2fbc13dcd46a): ZERO role assignments → Operation expired
- Azd env missing ALL Bicep outputs (AZURE_CONTAINER_REGISTRY_ENDPOINT, BACKEND_URL, etc.) because provision failed mid-way
- `azd deploy` failed: "could not determine container registry endpoint"

**Pattern confirmed:** All three Container Apps (backend, frontend, sandbox) exhibit the same failure mode independently, validating the diagnosis. This is a systematic issue, not a one-time anomaly.

## Solution
Two-phase RBAC assignment:
1. **Phase 1 (immediate post-identity-creation):** Grant ACR Pull ONLY — allows Container App to pull images
2. **Phase 2 (post-provisioning):** Grant all other permissions (Cosmos DB, AI Foundry, Storage)

## Implementation
Create `infra/modules/rbac-acr-only.bicep`:
- Takes backend/frontend/sandbox principal IDs as parameters
- Grants ONLY AcrPull role on ACR
- No dependencies on backend being healthy — just needs identity to exist

Update `infra/main.bicep`:
```bicep
// Immediate ACR access — no backend health dependency
module acrRbac 'modules/rbac-acr-only.bicep' = {
  name: 'rbac-acr'
  scope: rg
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    sandboxPrincipalId: sandbox.outputs.principalId
    acrName: acr.outputs.name
  }
}

// Full RBAC — runs after backend is healthy
module rbac 'modules/rbac.bicep' = if (deployRbac) {
  name: 'rbac'
  scope: rg
  dependsOn: [acrRbac]  // ACR access must exist first
  params: {
    // ... existing params ...
  }
}
```

Remove ACR Pull assignments from `rbac.bicep` (lines 142-178) since they're now in `rbac-acr-only.bicep`.

## Status
**Manual fixes applied:**
1. Backend identity (2026-05-22 07:08 UTC): AcrPull granted to e8b91c28-9125-4f2f-a64a-8a536fc8e66e
2. Frontend identity (2026-05-22 08:44 UTC): AcrPull granted to 6216b79f-7f75-4697-87de-6374f03bd4d9
3. Sandbox identity (2026-05-22 08:44 UTC): AcrPull granted to 92e01376-0bc6-46ef-aeda-2fbc13dcd46a
4. Azd env var fix (2026-05-22 08:44 UTC): `azd env set AZURE_CONTAINER_REGISTRY_ENDPOINT acr2mta7feoalzyq.azurecr.io`
5. **Role assignment collision fix (2026-05-22 09:15 UTC):** Deleted 3 manual role assignments that collided with Bicep deterministic naming

**Critical side effect discovered:** Manual `az role assignment create` uses RANDOM GUIDs. Bicep uses DETERMINISTIC GUIDs via `guid(scope, principalId, roleDefId)`. Subsequent `azd provision` fails with `RoleAssignmentExists` error because Azure enforces uniqueness on `(principal, role, scope)` triple — the assignment exists but with a DIFFERENT name. **Solution:** Delete manual role assignments before re-running provision, or use deterministic GUID when creating manual assignments.

**URGENT: Implement two-phase RBAC Bicep refactor BEFORE next full `azd down && azd up` cycle.**

**Next steps:**
1. Complete current deployment: `azd provision` → `azd deploy` (manual role assignments deleted, ready for Bicep to recreate with deterministic names)
2. Implement two-phase RBAC Bicep modules (detailed below) ASAP
3. Test full `azd down --purge && azd up` cycle to validate fix

## Related
- Container App stuck in "Failed" state with no revisions
- Logs: `infra/modules/rbac.bicep` lines 144-152 (ACR Pull assignment)

---

# Decision: Stdout/Stderr Discipline for azd Preprovision Functions

**Agent:** Verbal  
**Date:** 2026-05-20  
**Status:** Implemented  
**Category:** Infrastructure · DevOps · Shell Scripting

## Context

The `infra/scripts/select-model-regions.sh` preprovision hook was designed to query Azure for model availability and quota, then interactively prompt users to select regions. The selected regions should be persisted via `azd env set` for Bicep consumption.

**Problem:** The script ran successfully but never persisted the region selections. `.azure/turbo-voice/.env` showed other parameters (from `collect-deployment-params.sh`) were saved correctly, but `AZURE_OPENAI_LOCATION_PRIMARY/VOICE/RESEARCH` were missing. Bicep fell back to hardcoded `centralus` for voice, causing quota errors.

## Root Causes

### Bug A: Stdout Pollution in Command Substitution

Functions used for command substitution (`$(...)` or `readarray -t arr < <(...)`) wrote diagnostic output to stdout along with return values:

**`find_available_regions()`:**
- Wrote region scanning progress like `echo "Checking availability for: gpt-realtime gpt-4.1 ..."`
- Wrote per-region results like `echo "  Region eastus2:"`
- Final line `echo "${available_regions[@]}"` was the ONLY line intended for capture
- Result: `primary_regions[0]` became multiline garbage starting with "Checking availability..."

**`pick_region()`:**
- Wrote menu headers like `echo "Available regions for VOICE (with quota):"`
- Wrote numbered list like `echo "  1. eastus2"`
- Wrote confirmation like `echo "✅ Selected: eastus2"`
- Final line `echo "$selected"` was intended output
- Result: `VOICE_LOC=$(pick_region ...)` captured multiline garbage
- User never saw the menu because it was eaten by command substitution instead of displayed

**Impact:** `azd env set AZURE_OPENAI_LOCATION_VOICE "$VOICE_LOC"` with multiline garbage likely failed silently. Even with `set -euo pipefail`, azd proceeded to provision with no env var set, falling back to hardcoded defaults.

### Bug B: Nameref (`local -n`) Portability

`local -n models=$1` requires bash 4.3+. macOS system bash is 3.2; even with Homebrew bash 5, namerefs are fragile when passing arrays across function boundaries. Silent failures possible.

### Bug C: No Persistence Verification

Script assumed `azd env set` succeeded but never verified by reading back the value. Silent failures went undetected.

## Decision

**Enforce strict stdout/stderr discipline for all functions used in command substitution:**

1. **All diagnostic output → stderr (`>&2`):**
   - Progress messages: `echo "Checking availability..." >&2`
   - Menus and prompts: `echo "Select region:" >&2`
   - Confirmations: `echo "✅ Selected: eastus2" >&2`
   - Errors: `echo "❌ Failed..." >&2`

2. **Only return values → stdout:**
   - `echo "${available_regions[@]}"` (space-separated list)
   - `printf '%s\n' "$selected"` (single region)

3. **Interactive input from `/dev/tty`:**
   - `read -rp "Select region: " choice </dev/tty`
   - Ensures prompts work when stdin is piped under azd hook execution

4. **Replace namerefs with indirect expansion:**
   - `eval "local regions=(\"\${${regions_var}[@]}\"))"` for bash 3.2+ compatibility

5. **Explicit error handling:**
   - `trap 'echo "❌ ... failed at line $LINENO" >&2' ERR` after `set -euo pipefail`
   - Wrap each `azd env set` with `if ! azd env set ... ; then echo "❌ Failed..." >&2; exit 1; fi`
   - Final round-trip verification: `azd env get-value` after setting, exit 1 if mismatch

6. **Remove stale empty-string sets:**
   - Deleted `azd env set AZURE_OPENAI_LOCATION_* ""` calls (lines 352, 367, 382)
   - Setting empty doesn't unset — just clear local var and let prompt code handle it

## Implementation

**Files modified:**
- `infra/scripts/select-model-regions.sh` — applied all 6 fixes above

**Changes:**
- `find_available_regions()`: all echoes except final return use `>&2`
- `pick_region()`: all echoes except final return use `>&2`, `read </dev/tty`
- `check_az_login()`: all echoes use `>&2`
- `main()`: banner and subscription output use `>&2`
- Removed all `local -n` namerefs, replaced with `eval "local arr=(..."`
- Added ERR trap on line 7
- Wrapped all 3 `azd env set` calls with error checking
- Added final verification block in `main()` that reads back all 3 vars and exits 1 if mismatch

**Validation:**
- `bash -n` syntax check: ✅
- Manual code review: all diagnostic output confirmed using `>&2`
- Portability: no bash 4.x features remain

## Consequences

**Benefits:**
- **Persistent regions:** `azd env set` now receives clean single-line values → persistence works
- **User sees prompts:** Menu output goes to stderr → displayed to user instead of captured
- **Silent failures eliminated:** ERR trap + explicit `azd env set` checks + round-trip verification
- **Portable:** bash 3.2+ compatible (macOS system bash)

**Tradeoffs:**
- Slightly more verbose code (explicit `>&2` on many lines)
- Indirect expansion syntax less intuitive than namerefs

**Migration:**
- **No state to clear** — env vars were never written. Just re-run `azd up`.
- Picker will display menus correctly and persist selections

## Lessons Learned

1. **Command substitution capture discipline:**
   - Functions used in `$(...)` or `< <(...)` must treat stdout as a return channel ONLY
   - All human-facing output must go to stderr

2. **Interactive input under hooks:**
   - `read </dev/tty` is mandatory when script may run with piped stdin

3. **Nameref portability:**
   - Avoid `local -n` in portable shell scripts
   - Use indirect expansion via `eval` for bash 3.2+ compatibility

4. **Persistence verification:**
   - Never assume `azd env set` succeeded
   - Always read back with `azd env get-value` and verify match

5. **Error visibility:**
   - ERR trap + explicit checks + actionable error messages prevent silent failures

## Related

- `.squad/skills/azd-quota-aware-region-selection/SKILL.md` — added "Pitfalls" section documenting these three issues
- `.squad/agents/verbal/history.md` — added "Region Picker Stdout Pollution Fix" learning entry
- Quota dimension fix (2026-05-20) — prior fix that made region selection accurate
- Deployment parameter orchestrator (2026-05-19) — same stdout discipline pattern

## Alternatives Considered

**Alternative A: Use temporary files instead of command substitution**
- Write regions to `/tmp/regions.txt`, then `readarray -t regions < /tmp/regions.txt`
- Rejected: violates project security constraint (no /tmp usage), adds cleanup burden

**Alternative B: Keep stdout pollution, parse multiline output**
- Parse captured output with `grep`, `sed`, `awk` to extract clean value
- Rejected: fragile, error-prone, doesn't fix user visibility issue

**Alternative C: Suppress all output in non-interactive mode**
- Only show verbose output when TTY, silence when captured
- Rejected: complicates code, users want feedback during 30-60s region scan

## References

- Bash manual: https://www.gnu.org/software/bash/manual/bash.html#Redirections
- azd preprovision hooks: https://learn.microsoft.com/azure/developer/azure-developer-cli/azd-extensibility
- Bash portability guide: https://mywiki.wooledge.org/BashGuide/Practices

---


# Decision: Per-Model Quota Dimension Checking in Region Picker

**Date:** 2026-05-20  
**Status:** Implemented  
**Owner:** Verbal  
**Related:** `.squad/skills/azd-quota-aware-region-selection/SKILL.md`, `.squad/agents/verbal/history.md`

## Context

The `infra/scripts/select-model-regions.sh` preprovision hook was incorrectly passing regions as having quota for OpenAI models. Specifically, it offered `centralus` as having quota for `gpt-realtime`, but `azd up` deployment correctly failed with:

```
(!) Warning: Insufficient quota for model "gpt-realtime" (SKU: GlobalStandard) in centralus
  Requested: 10 · Available: 0
```

## Problem

**Root cause:** The `has_quota()` function checked for ANY `OpenAI.Standard.*` quota dimension with remaining quota:

```bash
# OLD CODE (too coarse)
az cognitiveservices usage list --location "$region" \
    --query "[?contains(name.value, 'OpenAI.Standard')].{current: currentValue, limit: limit}" -o json
```

This matched OTHER quota dimensions (e.g., `OpenAI.Standard.gpt-5.2`) with available quota, falsely passing the region even though `gpt-realtime` had zero quota.

**Evidence:**
- `az cognitiveservices usage list --location centralus` showed `OpenAI.GlobalStandard.gpt-realtime` at current=10, limit=10 (zero remaining)
- Azure quota is per-model, not per-SKU
- Quota dimension naming is EXACT: `OpenAI.<SKU>.<model-name>` (e.g., `OpenAI.GlobalStandard.gpt-realtime`)

## Decision

Rewrite quota checking to use EXACT per-model quota dimensions:

1. **Check exact quota dimension per model:**
   ```bash
   QUOTA_DIMENSION="OpenAI.${QUOTA_SKU}.${model_name}"
   az cognitiveservices usage list --location "$region" \
       --query "[?name.value=='$QUOTA_DIMENSION'].{current: currentValue, limit: limit}" -o json
   ```

2. **Define required capacity per model as parallel arrays:**
   ```bash
   PRIMARY_MODELS=("gpt-5.2" "gpt-4.1" "gpt-4o-transcribe")
   PRIMARY_CAPACITY=(500 500 200)
   
   VOICE_MODELS=("gpt-realtime")
   VOICE_CAPACITY=(10)
   
   RESEARCH_MODELS=("o3-deep-research")
   RESEARCH_CAPACITY=(1500)
   ```

3. **Region passes iff (limit - current) >= required_capacity for ALL models in the group.**

4. **Validate existing env vars on each run:**
   - If `AZURE_OPENAI_LOCATION_VOICE` is set to `centralus` but centralus no longer has quota for gpt-realtime, auto-clear the env var and re-prompt with warning.

5. **Verbose output by default:**
   - Print per-region per-model availability + quota during scan:
     ```
     Region eastus2:
       ✓ gpt-realtime — quota 10/10 available (need 10)
     Region centralus:
       ✗ gpt-realtime — quota 0/10 available (need 10) — SKIP
     ```

## Implementation

### Functions Added/Modified

- **`has_quota_for_model(region, model, required_capacity)`** — checks exact quota dimension `OpenAI.GlobalStandard.<model>`, returns 0 if `(limit - current) >= required_capacity`
- **`get_quota_info(region, model)`** — returns JSON with `{available, limit, current}` for verbose output
- **`is_model_available(region, model)`** — now also checks quota dimension exists (even if exhausted) to confirm model is deployable
- **`find_available_regions(models[], capacities[])`** — checks EVERY model in the group against its required capacity
- **Env var validation loop** — on each run, re-validate `AZURE_OPENAI_LOCATION_*` against current quota; auto-clear if insufficient

### Files Modified

- `infra/scripts/select-model-regions.sh` — complete rewrite of quota checking logic

### Capacity Values (from Bicep)

- **Primary Foundry (eastus2):** gpt-5.2=500, gpt-4.1=500, gpt-4o-transcribe=200
- **Voice Foundry (centralus):** gpt-realtime=10
- **Research Foundry (westus):** o3-deep-research=1500

## Consequences

### Positive

- ✅ Accurate quota checking — no more false positives
- ✅ Auto-recovery from stale env vars (e.g., centralus now exhausted)
- ✅ Verbose feedback during region scan (users see progress during 30-60s wait)
- ✅ Per-model quota awareness aligns with Azure reality

### Negative

- ⚠️ Region scan now slower (must query exact dimension per model per region, though cached per region)
- ⚠️ Pascal will be re-prompted for VOICE region on next `azd up` (centralus is now correctly detected as invalid)

## Alternatives Considered

1. **Keep coarse check, add manual override** — rejected, better to fix root cause
2. **Pre-query all quota dimensions at once** — attempted, but caching usage JSON per region achieves similar optimization
3. **Skip quota check, rely on azd preflight** — rejected, defeats purpose of interactive picker

## Validation

- ✅ `bash -n infra/scripts/select-model-regions.sh` — syntax check passed
- ✅ Dry-run query: `az cognitiveservices usage list --location eastus2 --query "[?name.value=='OpenAI.GlobalStandard.gpt-realtime']"` confirmed schema matches parser
- ✅ Capacity arrays match Bicep deployment values
- ⚠️ `azd up` NOT run (per user request)

## User Action Required

**Pascal:** Your azd env's `AZURE_OPENAI_LOCATION_VOICE=centralus` will be detected as invalid on next `azd up` and you'll be re-prompted to select a region with quota for gpt-realtime.

## References

- Azure quota dimension naming: `OpenAI.<SKU>.<model-name>`
- SKU for all current models: `GlobalStandard`
- Azure CLI quota query: `az cognitiveservices usage list --location <region>`
- Bicep capacity sources: `infra/modules/ai-foundry-{eastus2,centralus,westus}.bicep`

---


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


### 2025-11-25: Session pool replaces ACI + sandbox CA (Phase 1 infra)
**By:** Verbal (Infra/DevOps)
**Change:** sandbox-dynamic-sessions Phase 1
**What:**
- New `infra/modules/session-pool.bicep` provisions `Microsoft.App/sessionPools@2025-02-02-preview` (`containerType: CustomContainer`) inside the existing CAE. Pool has system-assigned MI; AcrPull granted in-module with deterministic `guid()` name.
- New `infra/modules/session-pool-role.bicep` grants the backend's MI `Azure ContainerApps Session Executor` (`0fb8eba5-…`) scoped to the pool, deterministic `guid()` name.
- Deleted: `container-app-sandbox.bicep`, `aci-network.bicep`, `aci-identity.bicep`, `aci-backend-role.bicep`. All wiring in `main.bicep` removed (incl. `enableAciSandbox`, ACI peerings, sandbox CA, sandbox-related `rbac.bicep` entries).
- Backend CA env vars: removed `SANDBOX_URL`, `USE_ACI_SANDBOX`, `ACI_*`; added `SESSION_POOL_MANAGEMENT_ENDPOINT`, `SESSION_POOL_NAME`, `SANDBOX_RUNTIME=session-pool`.
- New pool params with defaults: `sessionPoolMaxConcurrent=30`, `sessionPoolReadyInstances=1`, `sessionPoolCooldownSeconds=300`, `sessionPoolCpu=1.0`, `sessionPoolMemory=2Gi`, `sandboxImageTag=latest`.

**Why:** Replaces both ACI per-task containers and the shared `ca-sandbox-*` Container App with prewarmed Hyper-V-isolated sessions. Eliminates the placeholder-image catch-22 (deleted sandbox CA was the failure point) and the ARM-deploy-per-task cold start.

**Cycle fix:** backendFqdn passed to the pool is computed from the predictable `ca-backend-{token}.{cae.defaultDomain}` pattern (or `customDomainName` if set), not `backend.outputs.fqdn`, because the backend module also consumes `sessionPool.outputs.*` env vars. Without this, Bicep flags `BCP080` (cycle).

**Catch-22 mitigation:** Pool's own AcrPull and the backend→pool Session Executor role both use deterministic `guid(scope, principal, roleDef)` names per `.squad/skills/aca-provision-recovery/SKILL.md`. No manual `az role assignment create` workarounds needed.

**Validation:** `az bicep build --file infra/main.bicep` → exit 0, no errors. Only pre-existing warnings (ai-foundry `kind` BCP187, storage listKeys, hardcoded `core.windows.net`) remain.

**Follow-ups for Phase 2+ (not in scope):**
- `azure.yaml` `sandbox` service still uses `host: containerapp` — needs revisit; image push to ACR works but the CA-revision-update step has no target.
- `select-model-regions.sh` regional check for sessionPools (Risk table item) — defer.
- Backend code (Fenster) must read `SESSION_POOL_MANAGEMENT_ENDPOINT` / `SESSION_POOL_NAME`.


### 2026-05-22T13:34Z: Auth redirect URI — open-source audit
**By:** Pascal (via Copilot)
**What:** Login is NOT hardcoded to turboagent.nl. The redirect URI is already dynamically computed from `customDomainName` in Bicep, falling back to the ACA default FQDN if empty (`infra/modules/container-app-frontend.bicep:97`). `setup-entra-app.sh` registers the right redirect URIs from `CUSTOM_DOMAIN_NAME` + `FRONTEND_URL`. **No code changes needed for the auth flow itself.**

Cosmetic cleanup belongs in the `open-source-project` openspec change (NOT in `sandbox-dynamic-sessions`):
1. `infra/main.bicep:37` + `infra/modules/container-app-frontend.bicep:16` — replace `@description` example "e.g. voice.turboagent.nl" with `e.g. app.example.com`
2. `mobile/app.json:12` — keep `com.turboagent.voiceagent` (project name; only swap if rebranding mobile)
3. `frontend/playwright.prod.config.ts` + `e2e/production-verification.spec.ts` — parameterize via `PRODUCTION_URL` env var instead of hardcoded `voice.turboagent.nl`

**Why:** User flagged concern that login may not work when others deploy to their own tenant + domain. Audit confirms the architecture already supports this; only docs/examples need genericizing.


### 2026-05-22: Unified SandboxClient abstraction (Phase 3)
**By:** Fenster (for Pascal)
**What:** All sandbox HTTP traffic from `dev_agent.py` and the route layer now routes through a single `SandboxClient` Protocol. Two implementations live in `app/services/session_sandbox_client.py`:
- `SessionSandboxClient` — Azure Container Apps dynamic sessions (per-task isolation via `identifier`)
- `LocalSandboxClient` — docker-compose `http://sandbox:3000` (identifier ignored)

Selected at runtime by `get_sandbox_client()` singleton, which checks `SESSION_POOL_MANAGEMENT_ENDPOINT` env var. **No `USE_*` feature flag.** Code never branches on which sandbox runtime is active.

**Why:** Phase 2 introduced the session client but it wasn't wired in. Phase 3 makes the abstraction load-bearing so Phase 4 can delete ACI cleanly without further per-callsite churn. The unified surface also makes the local-dev story honest — same code path, different transport.

**Schema impact:** `SandboxState.containerAppUrl` → `sessionIdentifier`. Lazy upgrade: read tolerates legacy `containerAppUrl` field, write never emits it. No batch migration needed.

**ACI status:** `_provision_aci_sandbox`, `_start_aci_provisioning`, `_finish_aci_provisioning` are now no-op shims preserving their call sites. `_teardown_aci_sandbox` redirects to `client.stop_session()`. Phase 4 deletes the shims and `aci_sandbox_service.py` entirely.

### 2026-05-22: ACI sandbox path fully deleted (Phase 4)
**By:** Fenster
**What:** `backend/app/services/aci_sandbox_service.py`, the matching test module, the `USE_ACI_SANDBOX` env branch in `main.py` lifespan, the ACI orphan-cleanup background task, all `_provision_aci_sandbox` / `_start_aci_provisioning` / `_finish_aci_provisioning` shims and call sites in `dev_agent.py`, and the `ACI_IDENTITY_CLIENT_ID` branch in `sandbox/sync-skills.sh` are gone. The teardown helper that releases a per-task session is now named `_teardown_sandbox_session` to reflect its session-pool semantics.
**Why:** Phase 4 of OpenSpec change `sandbox-dynamic-sessions`. With the dynamic session pool in production (Phase 1+) and all callers on `SandboxClient` (Phase 3), the ACI code path was dead weight.
**Commit:** `88558ab`.

### 2026-05-22: Sandbox X-GH-Token is header-only on first call per dev-task (Phase 6)
**By:** Fenster
**What:** The sandbox dev pipeline no longer injects `ghToken` in the POST `/tasks` body. Instead, the backend attaches `X-GH-Token: <user_pat>` as an HTTP header on the FIRST `_sandbox_exec` call per dev-task (always the cleanup stage), and the sandbox container's Phase-5 middleware bootstraps `gh auth login --with-token` once. Tracked in memory via `_gh_token_sent: set[str]`; cleared by `cancel_sandbox_task_for` and `_teardown_sandbox_session`.
**Why:** Phase 6 of OpenSpec change `sandbox-dynamic-sessions`. The body-based path leaked the PAT on every request; the header-on-first-call pattern matches the session-lifetime semantics of the Container Apps dynamic session pool.
**Commit:** `fbaa199`.

### 2026-05-22: GitHub disconnect releases per-task sandbox sessions (Phase 6)
**By:** Fenster
**What:** `DELETE /api/me/connections/github-sandbox` now enumerates the calling user's dev-tasks in `{running, provisioning, pending}` and calls `SandboxClient.stop_session(task_id)` on each before clearing the stored PAT. Response body now includes `stoppedSessions` count. `app.state.dev_service` was added so the route handler can resolve the user's tasks without going through `dev_agent`.
**Why:** Phase 6 of OpenSpec change `sandbox-dynamic-sessions`. When a user disconnects GitHub, their in-flight sandbox seats must be released eagerly so the next run re-bootstraps gh-auth with the new (or absent) PAT.
**Commit:** `fbaa199`.

### 2026-05-22: Sandbox readiness marker file pattern (Phase 5)
**By:** Verbal
**What:** The sandbox container signals "skills synced" to the Container Apps session pool's Startup probe via a marker file at `/tmp/sandbox-state/skills-synced`. `entrypoint.sh` writes it after `sync-skills.sh` returns (regardless of success). `GET /ready` returns 200 iff the marker exists, else 503.
**Why:** Pool Startup probe polls `/ready` (5s × 30 attempts = 150s max). Marker file is the cleanest way to decouple the bash sync script from the Node server's readiness state without IPC. Writing the marker unconditionally even on blob-storage failure is intentional — spec requires `/ready` to succeed so the pool doesn't stall; users can retry via `POST /skills/sync`.

### 2026-05-22: X-GH-Token middleware contract (Phase 5)
**By:** Verbal
**What:** `server.js` adds an Express middleware that reads `X-GH-Token` from every request. First valid header value triggers `gh auth login --with-token` via stdin; in-process flag `ghAuthenticated` prevents repeat attempts on success. Header is stripped from `req.headers` after read. Token is never logged.
**Why:** Backend (Phase 6) injects the user's GitHub PAT as a per-session header instead of an ACI env var. The middleware must (1) auth idempotently, (2) handle concurrent first-requests (Promise guard), (3) never leak the token. On failure we log stderr (token-free) and allow the request to proceed — many sandbox endpoints don't need gh.

### 2026-05-22T14:00Z: azure.yaml sandbox host fix — hook-based ACR build (Phase 7 prep)
**By:** Pascal (via Verbal)
**What:** Removed the `sandbox` service from `azure.yaml` entirely. The image is now built directly into ACR by `infra/scripts/build-sandbox-image.sh` (azd `postprovision` + `postdeploy` hook) using `az acr build`, producing `${ACR}/turbo-voice-agent/sandbox:latest` — the exact tag the dynamic session pool references (`infra/main.bicep:263`).

**Options considered:**
- (a) `host: containerregistry` — azd does not document this as a stable host; risk of breakage.
- (b) **Chosen** — drop service entry, build via hook. Eliminates the misleading `host: containerapp` (the `ca-sandbox-*` Container App was deleted in Phase 1 and was the historical cause of 20-min "Operation expired" failures). Also replaces the older `tag-sandbox-latest.sh` push-then-retag dance with a single direct build.

**Why:** Phase 1 deleted the sandbox Container App. With no target, azd's `containerapp` host had nothing to update and re-introduced the deployment hang we were trying to escape. The session pool consumes the image directly from ACR; we only need a build/push, not a CA revision.

**Validation:** `az bicep build --file infra/main.bicep` clean. `bash -n` on both new scripts passes. Tag matches Bicep reference. Full `azd up` validation deferred to Pascal (Phase 9 wave).
**Commit:** `7861afd`.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction

# Decision: Azure Pipeline Audit & Fix — Session 2026-05-26

---
date: 2026-05-26
author: fenster-1 (audit), fenster-fix (implementation), verbal (runbook)
status: COMPLETED
confidence: HIGH
---

## Background

Pascal reported dev-task failures in Azure session-pool mode (after commit `909418a`):
- Tasks complete with "no visible error message"
- "Not authenticated in sandbox" errors
- `/api/sandbox/start` returns generic "stopped" without diagnostic detail
- `/api/sandbox/recreate` shows "Provisioning" but never clears

Three-agent session identified 7 findings and implemented fixes.

## Problem: 7 Findings (Audit)

### Blockers (2)

#### 1. Silent HTTPError in POST /tasks
**File:** `backend/app/agents/dev_agent.py:1408-1416`

POST /tasks → HTTP 4xx/5xx from pool (401/403 RBAC, 404 pool not found, 409 cooldown conflict, 429 concurrency cap, 5xx pool unhealthy) triggers `resp.raise_for_status()` → `httpx.HTTPStatusError` caught by outer try/except. Fallback code assumes task was submitted and polls for `sandbox_task_id` which was never assigned. Returns empty output; user sees no error.

**Fix:** Wrap `resp.raise_for_status()` in own try/except before SSE stream starts. Emit diagnostic message to stderr buffer when POST /tasks fails.

#### 2. gh-token ordering (skills-sync runs first without header)
**Files:** `dev_agent.py:2432-2495` (skills-sync), `dev_agent.py:1379-1384` (sandbox exec)

Skills-sync is FIRST sandbox call in every pipeline. It passes `identifier=task_id` (allocates session) but does NOT attach `X-GH-Token` header. Backend's `_gh_token_sent` tracker only checked in `_sandbox_exec` (called later), so `_sandbox_exec` may attach header to different session or first-call detection fails. gh-auth lands on wrong container.

**Fix:** Extract centralized `_maybe_attach_gh_token(task_id, headers)` helper. Call it in `_sync_skills_stage` BEFORE POST /skills/sync, and in `_sandbox_exec` as fallback (idempotent via tracker).

### High (1)

#### 3. Start probe error swallowing
**File:** `backend/app/routes/sandbox.py:44-69`

`_probe_sandbox_health()` bare `except Exception:` at line 68 catches all errors (401/403 RBAC not propagated, 404 pool not found, ConnectTimeout cold pool, TimeoutException). User sees `"status": "stopped"` with generic message; real error only in backend logs.

**Fix:** Catch `httpx.HTTPStatusError`, `httpx.ConnectError`, `httpx.TimeoutException` separately. Return error detail in 4-tuple; `/api/sandbox/start` surfaces it in response message.

### Medium (1)

#### 4. Recreate vestigial in pool mode
**File:** `backend/app/routes/sandbox.py:158-165`

Sets status to "provisioning" but releases no sessions. Pool is always live; no container restart. In ACI mode it restarted the CA instance. In pool mode: does nothing useful.

**Fix (Option B chosen by Pascal):** Enumerate user's active dev-tasks, call `client.stop_session(task_id)` for each. Return `{"stopped": [...]}`. Frontend button relabeled to "Release Sessions".

### Low (2)

#### 5. Status flip-flop on transient probe failure
**Files:** `sandbox.py:72-80`, `frontend/sandbox-config.tsx:51-56`

Frontend polls status every 15s. Probe timeout (5s) on occasional pool load causes transient failure → UI shows "Stopped" → next poll succeeds → flickers back to "Ready". UX confusing.

**Fix:** Add hysteresis or increase timeout to 10s in pool mode.

#### 6. Premium baseline tracking (OK — verified preserved)
**File:** `backend/app/routes/sandbox.py:25-30, 51-69, 102-113`

Verified correct. Preserved in commit `909418a`. No regression.

### OK (1)

#### 7. Cosmos lazy upgrade handles containerAppUrl (OK — verified correct)
**File:** `backend/app/services/sandbox_service.py:36-52`

Tolerates legacy `containerAppUrl` field. No blocking issue.

---

## Solution: Four Fixes Implemented (Fenster-Fix)

### Fix 1: gh-token → FIRST call
**Commit:** `2a7e013`  
**Files:** `backend/app/agents/dev_agent.py` lines 2432–2450

Centralized helper `_maybe_attach_gh_token(task_id, headers)` checks `_gh_token_sent` and adds header if needed. Both `_sync_skills_stage` and `_sandbox_exec` call it. Skills-sync now attaches header on first allocation.

### Fix 2: Surface pool 4xx/5xx errors
**Commit:** `2a7e013`  
**Files:** `backend/app/agents/dev_agent.py` lines 1403–1428

POST /tasks wrapped in own try/except catching `httpx.HTTPStatusError` specifically. On error: build diagnostic message (status + truncated body), log ERROR, emit `{"type": "stderr", ...}` to pipeline output buffer, re-raise as RuntimeError.

### Fix 3: Granular start probe errors
**Commit:** `2a7e013`  
**Files:** `backend/app/routes/sandbox.py` lines 44–87, 99, 265–278

`_probe_sandbox_health()` returns 4-tuple: `(reachable, active, premium, error_detail | None)`.
- Catch `httpx.HTTPStatusError` separately (include status + truncated body)
- Catch `httpx.ConnectError` separately ("Pool unreachable (network/DNS issue)")
- Catch `httpx.TimeoutException` separately ("Pool cold (no response within 5s)")
- `/api/sandbox/start` surfaces `error_detail` in response message

### Fix 4: Recreate releases sessions
**Commit:** `2a7e013`  
**Files:** `backend/app/routes/sandbox.py` lines 158–199, `frontend/sandbox-config.tsx` lines 210–217

Enumerate user's dev-tasks via `dev_service.with_user(user_id).list()`, filter to `{running, provisioning, pending}`, call `client.stop_session(task_id, reason="recreate")` for each (best-effort), return `{"status": "ready", "stopped": [task_ids]}`.

---

## Test Coverage

**Boundary exception:** Fenster-fix included test implementation (normally Kobayashi's domain) because fixes were tightly coupled to test surface. 39 tests added/updated, all passing.

**Updated:** `test_dev_agent_gh_token.py` (2 new tests)

**New:**
- `test_dev_agent_pool_errors.py` (3 tests: 403, 429, 500 diagnostics)
- `test_sandbox_probe_errors.py` (4 tests: probe error detail, error types, endpoint surface)
- `test_sandbox_recreate.py` (3 tests: stop sessions, no-op, error handling)

**Verification:**
```bash
pytest tests/test_dev_agent_gh_token.py \
       tests/test_session_sandbox_client.py \
       tests/test_sandbox_disconnect.py \
       tests/test_dev_agent_pool_errors.py \
       tests/test_sandbox_probe_errors.py \
       tests/test_sandbox_recreate.py -v
# ✅ 39 passed in 1.09s
```

---

## Azure Validation Runbook (Verbal)

Produced complete, copy-pasteable runbook for Pascal to execute. 6 phases with commands that auto-resolve resource names via `azd env get-values`.

**Location:** `.squad/decisions/inbox/verbal-azure-validation-runbook.md` (merged from inbox)

**Phases:**
- A.1: Pre-flight (backend revisions, pool status, image staleness)
- A.2: Pool refresh (delete & reprovision or wait)
- A.2.2: Deploy latest backend
- A.3: Trigger controlled failures
- A.4: Capture logs
- B: Triage output template

**Status:** Awaiting Pascal to execute and provide triage output.

---

## Ancillary Decisions (Merged from Inbox)

### Sandbox image build moved to preprovision (Verbal, 2026-05-22T15:30Z)

After UAMI ACR-Pull fix (`efd6565`), `azd provision` failed at session pool with "crashing pods" due to stale sandbox image. Phase 5 code additions (`/health`, `/ready` endpoints) built at 2026-05-22T11:43, but image was from 11:17 (26 min prior) — probes hit 404s → pods killed.

**Fix:** Added `bash infra/scripts/build-sandbox-image.sh` to `preprovision` hook in `azure.yaml` (in addition to existing `postprovision`/`postdeploy`). Script safe-exits 0 when `AZURE_CONTAINER_REGISTRY` unset (first run); on subsequent runs, image rebuilt before pool is reconciled, eliminating staleness window.

**Immediate recovery:** Manually built image, deleted failed pool, Pascal can re-run `azd provision`.

**Commit:** Included in Phase 5 work (Verbal domain).

### Session pool uses pre-granted UAMI for ACR Pull (Verbal, 2026-05-22T14:30Z)

Switched from system-assigned managed identity to user-assigned UAMI (`id-sandbox-pool-${resourceToken}`) granted `AcrPull` on registry in separate module deployed BEFORE pool creation. Eliminates RBAC propagation race (5–10 min delay after identity creation).

**Commit:** Bicep changes in Phase 4 work.

### X-GH-Token middleware contract (Verbal, Phase 5)

Express middleware reads `X-GH-Token` header on every request. First valid header triggers `gh auth login --with-token` via stdin. In-process flag `ghAuthenticated` prevents repeat attempts. Header stripped after read (never logged).

**Design:** Backend (Phase 6) injects user's GitHub PAT as per-session header instead of ACI env var. Middleware must auth idempotently and never leak token.

**Commit:** Phase 5 sandbox code.

### Sandbox readiness marker file pattern (Verbal, Phase 5)

Sandbox container signals "skills synced" via marker file `/tmp/sandbox-state/skills-synced`. `entrypoint.sh` writes unconditionally after `sync-skills.sh` returns (regardless of blob sync success). `GET /ready` returns 200 iff marker exists, else 503.

**Why:** Pool Startup probe polls `/ready` (5s × 30 attempts). Marker decouples bash sync script from Node server readiness without IPC. Unconditional marker write is intentional — allows probe to pass even if blob storage fails; users can retry via `POST /skills/sync`.

**Commit:** Phase 5 sandbox code.

### Sandbox /tasks handler stale validation gate (Fenster handshake diagnosis, 2026-05-22T18:00Z)

Root cause of 400 Bad Request on first dev-task POST /tasks in session-pool mode: handler checks `effectiveToken = perTaskToken || process.env.GH_TOKEN` for prompt-based tasks. In pool mode:
- No `GH_TOKEN` env var (shared ephemeral containers, not per-user)
- Backend stopped sending `ghToken` in body (Phase 6 move to header)
- Middleware authenticated `gh` from `X-GH-Token` header but handler doesn't consult `ghAuthenticated` flag

**Proposed fix (Phase 5 follow-up):** Add `&& !ghAuthenticated` to the validation gate in `sandbox/server.js` POST /tasks handler (lines ~138–183).

**Status:** Flagged for Verbal to implement sandbox-side fix.

### Skill-sync architecture is correct (Fenster handshake diagnosis)

`sync-skills.sh` designed for per-user long-lived ACI containers, but reusable in dynamic pool:
- Containers ephemeral but shared (not per-user)
- Skills not user-scoped on disk (installed system-wide)
- User activation state in Cosmos, enforced backend-side
- `sync-skills.sh` at startup still works (just needs MSI + storage RBAC wired through)
- Lazy `POST /skills/sync` endpoint already in `sandbox/server.js` and called by backend

**Status:** No architectural change needed. MSI + storage config verification needed (Verbal's domain).

### Premium request baseline tracking (verified OK)

Logic for tracking premium-request counts survives pool-mode rewrite. No regression.

### Cosmos schema lazy upgrade tolerates legacy containerAppUrl field

Sandbox service `_doc_to_model` accepts `containerAppUrl` field from legacy docs, ignores it. `_model_to_doc` never writes it. No blocking issue.

### Phase 8 deferral: App Insights custom events

Emit `sandbox.session.allocated` / `sandbox.session.stopped` as structured `logging` records with `extra={"event": "sandbox.session.*", ...}` rather than wiring opencensus / azure-monitor-opentelemetry into backend lifespan. This allows App Insights integration later without modifying agent code.

**Commit:** Phase 8 note (deferred implementation).

### Phase 9 local test sweep (Kobayashi)

Local test sweep of `sandbox-dynamic-sessions` work (all 9 phases) ready pending fixup of the two audit-identified BLOCKERS (gh-token ordering, silent HTTPError). Once `2a7e013` is deployed, Kobayashi to re-run e2e suite.

---

## Notes for Next Session

- **Verbal:** Verify `/skills/sync` response on pool (0 skills → blob storage not mounted? MSI RBAC missing?). Sandbox-side `/ready` issue flagged for investigation.
- **Kobayashi:** Review test coverage, assertion clarity, and mock hygiene in fenster-fix boundary-exception tests.
- **Pascal:** Execute Verbal's Azure validation runbook (Phase A.1–A.4) to provide triage data.
- **All:** Silent error modes now visible; expect user-facing improvements in dev-task observability.

---


---

# Decision: Transient Pool Allocation Retry Shipped

**Agent:** Fenster  
**Status:** Shipped  
**Commit:** `986f326392de2da95eb8e1109a4fd1e54ead3608`

## Retry parameters

- Scope: backend `_sandbox_exec` POST `/tasks` only.
- Attempts: 3 total attempts.
- Backoff: exponential 1s → 2s → 4s policy with ±25% jitter. With 3 total attempts, sleeps occur before retry attempts using the 1s and 2s slots; the 4s slot is retained as the next value for the same policy shape.
- User stderr: emitted only after final failure, preserving the existing terminal error schema.
- Internal observability: retryable attempts log `sandbox.session.transient_retry` with identifier, attempt, max attempts, status code, and latency.

## Trigger conditions

Retry is enabled for:

- HTTP 5xx from the session pool.
- HTTP 429.
- Response body containing `Error happened when allocating pod` regardless of status.
- Response body containing `sessionpool` with status >= 500.
- `httpx.ConnectError`, `httpx.ReadTimeout`, and `httpx.PoolTimeout`.

Do not retry:

- HTTP 4xx except 429, including auth/bad-request failures such as `400 missing token`.

---

# Decision: Fenster — Sandbox token Cosmos fallback

**Date:** 2026-05-27
**Author:** Fenster
**Status:** Implemented

## Problem

After a backend redeploy, the process-local `_connection_store` is empty. `get_sandbox_user_token()` only read that cache, so the first dev-task for a user could omit `X-GH-Token` even though the user's encrypted `githubSandboxToken` was persisted in Cosmos. The sandbox then rejected prompt-based tasks with HTTP 400: `GitHub token required`.

## Fix

`get_sandbox_user_token(user_id, profile_service)` now keeps cache-first behavior, then falls back to `UserProfileService.get_profile(user_id)` on cache miss. When Cosmos contains `githubSandboxToken`, the helper warms `_connection_store`, decrypts the token, and returns it for the dev pipeline. The dev agent passes its injected profile service into this helper during `run_pipeline()`.

## Observability

When the Cosmos fallback recovers a cold cache, the backend logs structured event `sandbox.user_token.cache_miss_recovered` with `user_id` and `source: "cosmos"`.

## Verification

Added tests for cache hit/no Cosmos read, cache miss with Cosmos token/cache warm, and cache miss with no Cosmos token. Focused token tests pass. Full repo lint/test commands were also run; they currently fail on pre-existing unrelated backend formatting/lint and notes API baseline issues.

---

# Decision: Dev-task stream lacks structured agent events

**Author:** McManus
**Date:** 2026-05-27
**Status:** PROPOSAL — Option A Selected (Draft OpenSpec Proposal in Future Session)

## Finding

Production logs for dev task `d9cc6118-7805-45b0-9433-1c38a5c8af56` show the backend did start and execute dev-task stages (`cleanup`, `init`, `squad-*`, `implement`, `screenshots`). The SSE endpoint was also opened successfully by the browser.

The current event pipeline is:

1. `sandbox/server.js` spawns raw commands or `copilot -p ... --agent squad --autopilot ...`.
2. The sandbox stream endpoint emits only stdout/stderr/exit entries as anonymous SSE `data:` messages.
3. `backend/app/agents/dev_agent.py::_sandbox_exec` appends those entries to the module-level pipeline buffer, adding coarse `stage` / `stage_exit` markers.
4. `backend/app/routes/dev.py` re-streams the buffer via `/api/dev/{task_id}/stream`, also as anonymous SSE `data:` messages.
5. `frontend/src/app/(app)/development/[id]/page.tsx` renders only `stdout`, `stderr`, `stage`, and `decision` entries in the terminal; stage and squad UI state comes from polling `devApi.get()`.
6. `frontend/src/app/(app)/agents/page.tsx` does not subscribe to dev-task SSE or active dev-task events.

## Root cause

There is no structured agent-event contract in the current pipeline. Expected events like `Architect started`, `Coder started`, or per-agent progress are not emitted as first-class `agent_start` / `agent_progress` / `agent_complete` events. Squad activity is only inferred by regex from stdout lines in `_sandbox_exec`, and those inferred updates are stored on the dev task for polling, not streamed as typed SSE events.

## Recommended fix (Option A)

Introduce explicit pipeline buffer event types for `stage_start`, `stage_complete`, `agent_start`, `agent_progress`, and `agent_complete` around squad setup, Copilot CLI execution, and parsed squad status.

Backend: optionally emit named SSE `event:` fields in `routes/dev.py` while keeping the existing `data:` payload for backward compatibility.

Frontend detail page: render the new event types in the terminal/activity timeline and update squad state optimistically from SSE instead of relying only on 2s polling.

Frontend agents page: either show active dev-task activity by polling `devApi.list()`/active task detail, or subscribe to a new aggregate dev-task activity stream if backend provides one.

## Risk

Small risk to existing terminal streaming if old `stdout`/`stderr` entries are preserved. Higher risk if named SSE events replace anonymous `message` events; use additive event types first to avoid breaking current clients.

## Decision Made

**Pascal selected Option A:** Draft an OpenSpec proposal in a future session with Redfoot to design the typed agent-event SSE contract, backend implementation, and frontend rendering.

---

# Decision: Transient Pool Allocation Errors in Dev-Task Stream

**Date:** 2026-05-27  
**Scope:** UX handling of pool-level transient failures during sandbox execution  
**Context:** Task `d9cc6118-...` experienced a transient pool allocator failure ("Error happened when allocating pod..."), retried at iteration level, and eventually succeeded. User saw the scary error in the dev-task output stream even though recovery happened.

## The Issue

When Azure Container Apps session pool returns a transient error (e.g., capacity blip, cold-start pod scheduling delay), our new error-surfacing code (commit 2a7e013) writes it to the dev-task stderr stream. Users see:

```
Error happened when allocating pod for identifier d9cc6118-... in pool sp-sandbox-...
```

even though the pipeline auto-recovers on retry. **Poor UX:** scary error for non-critical transient condition.

## Recommendation

**Option A: Add transient-retry inside `_sandbox_exec` with exponential backoff.**

Smart retry logic (3 attempts, 1s/2s/4s backoff) for transient-class errors only (5xx, 429, pool allocator messages). Prevents transient errors from ever hitting the stderr stream. Users only see errors that are real (after all retries exhausted).

**Rationale:** Transient pool errors are part of normal operation (cold starts, capacity squalls). Production systems silently recover from these. Hidden transients ≠ hidden signals — log the retries internally for debugging, but don't surface to user unless final failure.

## Implementation Notes

- Scope the retry to `SessionSandboxClient.request()` or wrap specific call sites in `_sandbox_exec`
- Detect transient: status ≥ 500, status = 429, body contains "allocat" or "pod" + "error"
- Log internal retry attempts at DEBUG level for observability
- Abort retry loop only on 4xx (real errors) or max attempts exhausted
- Don't change iteration-level retry behavior (that's separate concern)

**Status:** Implemented via commit `986f326` (Option A shipped).

---

# Decision: X-GH-Token Validation Gate — No Code Change

**Date:** 2026-05-27
**Status:** Diagnosed + Decision = No Fix Needed
**Scope:** Session pool allocation + sandbox authentication
**Owners:** Verbal (diagnostic), Pascal (user action)

## Summary

Dev-task failed during sandbox allocation with backend HTTP 400: `"GitHub token required — set it in Settings → Connections"`. Root cause: user has not configured a GitHub personal access token (PAT) in the app under Settings → Connections. When missing, `backend/app/routes/user.py:get_sandbox_user_token()` returns `None`, and `dev_agent` cannot send the required `X-GH-Token` header on the first sandbox request. Sandbox validation gate correctly rejects the task.

**Decision:** No code fix. The system is working as designed. User action required.

## Root Cause Analysis

### Call Path
1. **Dev-task starts** → `dev_agent.run_pipeline(task_id, user_id, ...)`
2. **Phase 1: Skills sync** → `_sync_skills_stage(task_id)` makes first sandbox call
3. **Token resolution** → `await get_sandbox_user_token(user_id)` queries Cosmos DB
4. **Lookup fails** → `_connection_store.get(f"sandbox:{user_id}")` returns None (user never set a GitHub PAT)
5. **No header sent** → `dev_agent._maybe_attach_gh_token()` skips adding X-GH-Token because `gh_token` is None
6. **Sandbox rejects** → `sandbox/server.js` validation gate line 179 checks `if (!effectiveToken && !ghAuthenticated)` and returns 400
7. **Container fails** → Startup probe fails, pool reports allocation error

### Why This Is Expected

The sandbox container requires a GitHub token to bootstrap `gh auth login --with-token` (Phase 5 of `sandbox-dynamic-sessions` architecture). Without it:
- Container cannot authenticate as the user with GitHub
- Cannot run `gh` CLI commands (gists, repo interactions)
- Cannot clone or push to Git repositories
- Must reject the request at validation time (not midway through execution)

The message `"set it in Settings → Connections"` is the correct user-facing error.

## Evidence

**Backend logs** (Log Analytics, task `d9cc6118-7805-45b0-9433-1c38a5c8af56`):
```
2026-05-27 08:38:29.014 ERROR app.agents.dev_agent
  Sandbox pool rejected task (HTTP 400):
  {"error":"GitHub token required — set it in Settings → Connections"}
```

**Pool status:**
- `provisioningState: Succeeded` (healthy)
- Identity: UAMI `id-sandbox-pool-2mta7feoalzyq` with AcrPull (working)
- Image: `acr2mta7feoalzyq.azurecr.io/turbo-voice-agent/sandbox:latest` (correct)

**Earlier same day:** Tasks completed successfully — those dev-tasks likely came from users who HAD GitHub tokens configured.

## Decision

### No code fix required
- Validation logic is correct
- Sandbox correctly rejects tasks without GitHub auth
- Backend correctly forwards user's PAT when available, omits when missing

### No UI/UX fix needed
- Error message is clear: "set it in Settings → Connections"
- User has the information needed to resolve

### What will make it work
**Pascal's immediate action:**
1. Open app → Settings → Connections
2. Add GitHub Personal Access Token (repo + gist scopes, or broader)
3. Save (encrypted, stored in Cosmos DB under `sandbox:{user_id}`)
4. Trigger new dev-task
5. Backend loads token, sends `X-GH-Token`, sandbox accepts, task runs

## Diagnostic Pattern For Future

Session pool allocation errors are often opaque at the infrastructure level:

| Symptom | Investigation Path |
| --- | --- |
| "Error happened when allocating pod for identifier X in pool Y" | Check **backend container logs** for the real HTTP error from SessionSandboxClient |
| Allocation fails but pool state is Succeeded | Examine container startup logic (probes, entrypoint). The pool is fine; the container crashed. |
| Intermittent failures | If earlier tasks succeeded, it's usually data-plane (user config) not infrastructure (pool, image, RBAC) |

**Log queries to run:** `ContainerAppConsoleLogs_CL` filtering for identifier and `sandbox.session.error` events in backend logs.

## References

- `backend/app/services/session_sandbox_client.py` — X-GH-Token forwarding
- `backend/app/agents/dev_agent.py` — Token loading + attachment logic
- `backend/app/routes/user.py:get_sandbox_user_token()` — Cosmos DB lookup
- `sandbox/server.js:L179` — Validation gate
- `.squad/agents/verbal/history.md` → Phase 5 learnings (2026-05-22)

---

**No follow-up work needed.** System is functioning as designed.

# Decision: Mockup Pipeline Fail-Fast and Readiness Hardening

---
date: 2026-05-27
author: fenster
status: SHIPPED
confidence: HIGH (verified by 44 focused tests)
---

## Problem

Task `ba04ba04-2620-440c-a7d0-20d093355097` produced misleading success: the implement stage encountered a sandbox submission failure, but the pipeline still checkpointed and advanced to screenshots. The fallback preview path then accepted a 404 `Cannot GET /` response as "ready" because readiness validation allowed any status below 500.

**Root causes:**
1. **Implement-stage exceptions swallowed:** Error handler in `dev_agent.py:_run_mockup_stage()` logged but did NOT abort. Pipeline continued despite failure.
2. **Readiness too lenient:** Health check allowed `status < 500` instead of requiring `200 <= status < 300`. Fallback/static servers (4xx) passed validation.
3. **Missing guard:** Mockup description could be empty or garbage if spec generation partially failed. No pre-check on content length.

## Solution

Hardened `backend/app/agents/dev_agent.py` with three scoped fixes:

1. **Fail-fast on pre-screenshot stages**
   - `init`, `skills`, `implement` now abort the mockup pipeline when:
     - Sandbox execution returns non-200 status
     - Exception is raised
     - Process exits non-zero
   - Task and active stage are marked failed; clear terminal error emitted

2. **Strict preview readiness**
   - Health check now requires `200 <= status < 300` (no 4xx fallback)
   - Timeout message: `❌ Preview server never returned 2xx on localhost:3000 — mockup did not start. Last status: {status}.`

3. **Guard mockup description**
   - Implement validates `mockup_desc` is non-empty string with >= 20 characters
   - Aborts with spec-id diagnostic if invalid

## Rationale

Multi-stage pipelines should fail loudly at the first stage that leaves workspace unusable. Continuing after init/skills/implement failure creates misleading downstream artifacts, wastes sandbox time, and hides the real cause from users. Readiness checks must prove the generated app is serving a successful route, not merely that an HTTP server responded with *any* status.

## Testing

- 44 focused pytest tests: all pass
- Scenarios covered: init/skills/implement abort, readiness status checks, spec-id validation
- Commit: `2c1a876`

## Status

**SHIPPED** (commit `2c1a876`). Pipeline now fails loudly at first unusable stage, preventing misleading downstream artifacts.

---
