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

**URGENT: Implement two-phase RBAC Bicep refactor BEFORE next full `azd down && azd up` cycle.**

**Next steps:**
1. Complete current deployment: `azd provision` → `azd deploy` (should succeed now that RBAC is fixed for all apps)
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


## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
