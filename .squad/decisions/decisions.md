# Team Decisions

## Verbal — Quota-Aware OpenAI Region Selection

**Author:** Verbal  
**Date:** 2026-05-19  
**Status:** Implemented

### Problem

`azd up` was failing for new users because we hardcoded OpenAI model deployment regions (eastus2, westus, centralus) in `infra/main.bicep`. When users attempted to deploy on subscriptions without quota in those specific regions, the deployment would fail with cryptic ARM template errors.

This created a poor first-run experience for the OSS project — users hit quota limits before ever seeing the app run.

### Solution

Implemented a quota-aware, interactive region selection as an `azd` preprovision hook.

**New script:** `infra/scripts/select-model-regions.sh`

The script:
1. Queries Azure's Cognitive Services API to determine which regions have each required model available
2. Checks quota availability in each candidate region using the usage API
3. For each of the 3 Foundry accounts, presents regions where ALL models in that group are available AND have quota
4. Prompts the user to select a region (numbered list, defaults marked)
5. Stores selections as azd environment variables (`AZURE_OPENAI_LOCATION_PRIMARY`, `AZURE_OPENAI_LOCATION_VOICE`, `AZURE_OPENAI_LOCATION_RESEARCH`)

**Idempotency:** If the env vars are already set, the script skips all prompts and exits immediately. This makes `azd up` re-entrant — you can re-run provisioning without being re-prompted.

**Non-interactive mode:** For CI/CD pipelines (e.g., GitHub Actions), the script detects non-TTY stdin and requires all three env vars to be pre-set. It fails fast with a clear error message listing the required variables.

**Candidate regions:** eastus, eastus2, westus, westus2, westus3, northcentralus, southcentralus, centralus, swedencentral, westeurope, francecentral, uksouth, japaneast, australiaeast. This list is intentionally broad because some models (e.g., o3-deep-research) are only available in 2-3 regions globally.

### Infrastructure Changes

- **`infra/main.bicep`**: Added 3 new parameters (`primaryAiLocation`, `voiceAiLocation`, `researchAiLocation`) with defaults matching the old hardcoded values. Replaced hardcoded `location: 'eastus2'`, `'westus'`, `'centralus'` with these params.
- **`infra/main.parameters.json`**: Added the 3 new params with azd env var substitution (e.g., `${AZURE_OPENAI_LOCATION_PRIMARY=eastus2}`).
- **`azure.yaml`**: Preprovision hook now runs `select-model-regions.sh` BEFORE `setup-entra-app.sh` (fail-fast on quota). Added the 3 env vars to pipeline variables for GitHub Actions.
- **`README.md`**: Documented the interactive region selection behavior, manual override via `azd env set`, and CI requirements.

### Model Groups

We deploy 3 separate AI Foundry accounts, each hosting a logical group of models:

1. **Primary Foundry** (default: eastus2)
   - gpt-5.2
   - gpt-4.1
   - gpt-4o-transcribe

2. **Voice Foundry** (default: centralus)
   - gpt-realtime

3. **Research Foundry** (default: westus)
   - o3-deep-research

The script ensures that for multi-model groups (e.g., Primary), a region is only offered if ALL models in that group are available with quota.

### Detection Approach

**Model availability:**
```bash
az cognitiveservices model list --location <region>
```
Returns JSON array of available models. If the model name is present, it's available in that region.

**Quota check:**
```bash
az cognitiveservices usage list --location <region>
```
Returns quota dimensions (e.g., `OpenAI.Standard.*`). The script parses the JSON and checks if `currentValue < limit` for any OpenAI.Standard dimension. This is a conservative heuristic — quota is reported at the account level, not per-model, so we assume if ANY OpenAI.Standard quota exists, deployment is viable.

**Edge case:** If no regions have quota, the script prints an actionable error message with instructions to request a quota increase in Azure Portal or manually override via `azd env set`.

### Benefits

- **First-run reliability:** Users no longer hit quota errors on `azd up` — they're guided to regions that work
- **Transparency:** The script shows which regions have quota, so users understand resource availability in their subscription
- **CI-friendly:** Non-interactive mode fails fast with clear instructions
- **Idempotent:** Re-running `azd up` doesn't re-prompt
- **Backwards-compatible:** Defaults match the old hardcoded values, so existing deployments aren't forced to migrate

### Alternatives Considered

1. **Document manual override only** — rejected because it's poor UX (every new user would hit the error and have to debug)
2. **Auto-select first available region** — rejected because users should be aware of region choice (latency, compliance, cost)
3. **Per-model quota check** — not feasible; Azure quota API doesn't expose per-model granularity for OpenAI deployments

### Validation

- ✅ Script syntax: `bash -n` passes
- ✅ Bicep compilation: `az bicep build` succeeds (pre-existing warnings unaffected)
- ✅ JSON/YAML syntax: valid
- ✅ Non-interactive guard: tested with `[ ! -t 0 ]` condition

---

## Redfoot — OSS Release: Open-Source Preparation Strategy

**Author:** Redfoot  
**Date:** 2026-03-29  
**Status:** Proposed (pending approval)

### Decision

The project will be prepared for open-source release following a comprehensive audit and scrubbing process that ensures no personal identifiers, credentials, or environment-specific configuration remain in the codebase or git history.

### Key Choices

1. **MIT License** — Selected MIT over Apache 2.0 or GPL for its simplicity and permissiveness, aligning with reference implementation goals.
2. **Decommission-Then-Redeploy Validation** — Existing Azure deployment will be torn down via `azd down --force --purge` and redeployed from scratch to validate that instructions work end-to-end for new users.
3. **Multi-Pass Scrubbing Strategy** — Automated grep searches for known patterns (names, emails, GUIDs) combined with manual audit of high-risk files (Bicep, workflows, env examples).
4. **Parameter-First Infrastructure** — All Bicep templates will use parameters declared in `azure.yaml` with no hardcoded personal values. Required parameters documented with descriptions.
5. **README as Primary Onboarding** — Complete README rewrite structured for deployment (manual + automated) as the primary user journey, with local development as secondary.
6. **.squad/ Folder Treatment** — `.squad/` folder will remain in repository but documented as project-specific local metadata (safe to ignore for new users).
7. **GitHub Actions Workflow Preserved** — Existing CI/CD workflow kept as-is, with all personal values extracted to repository variables that users configure post-fork.

### Impact

- **Documentation:** Major README rewrite, addition of 3 governance documents (LICENSE, CODE_OF_CONDUCT.md, SECURITY.md)
- **Infrastructure:** All Bicep files must be audited and parameterized
- **Timeline:** Decommission scheduled as final step before repository goes public (minimize downtime)
- **Risk:** If redeployment fails, OSS release delayed until instructions validated

---

## Kobayashi — Slides pipeline test note

**Date:** 2026-05-19

I updated the slides-stage regression coverage in tests only.

- `backend/tests/test_slides_service.py` now verifies slides-mode tasks expose exactly three stages drawn from `init`, `slides`, and `run`.
- The backend assertion explicitly rejects the removed `skills` stage.
- The assertion is set-based instead of order-based because the current service still emits `run` before `slides`; this keeps the regression focused on the stage rename/removal requested in task 7.4 without changing production code from the tester role.
- `frontend/e2e/dev-task-e2e.spec.ts` now expects the visible slides labels `Init`, `Slides`, and `Run`.

Follow-up for implementers: if stage order matters contractually, production code still needs a separate fix to emit `init → slides → run` consistently.

---

## Verbal — Region Picker Stdout/Stderr Discipline

**Author:** Verbal  
**Date:** 2026-05-20  
**Status:** Implemented

### Problem

The `select-model-regions.sh` preprovision hook ran successfully but never persisted the selected regions to azd environment variables. `.azure/turbo-voice/.env` showed other parameters (from `collect-deployment-params.sh`) were saved correctly, but `AZURE_OPENAI_LOCATION_PRIMARY/VOICE/RESEARCH` were completely missing. Bicep fell back to hardcoded `centralus` for voice, causing quota errors.

### Root Causes

**Bug A: Stdout Pollution in Command Substitution**

Functions used for command substitution (`$(...)` or `readarray -t arr < <(...)`) wrote diagnostic output to stdout along with return values. For example:

- `find_available_regions()` wrote region scanning progress like `echo "Checking availability for: gpt-realtime..."` to stdout
- `pick_region()` wrote menu headers, numbered lists, and confirmations to stdout
- The final `echo "${available_regions[@]}"` or `echo "$selected"` was the ONLY line intended for capture

Result: `primary_regions[0]` became multiline garbage starting with "Checking availability...". `VOICE_LOC=$(pick_region ...)` captured the entire menu instead of just the selected region. `azd env set AZURE_OPENAI_LOCATION_VOICE "$VOICE_LOC"` with multiline garbage likely failed silently. Even with `set -euo pipefail`, azd proceeded to provision with no env var set.

**Bug B: Nameref Portability**

`local -n models=$1` requires bash 4.3+. macOS system bash is 3.2; even with Homebrew bash 5, namerefs are fragile when passing arrays across function boundaries. Silent failures possible.

**Bug C: No Persistence Verification**

Script assumed `azd env set` succeeded but never verified by reading back the value. Silent failures went undetected.

### Solution

**Enforce strict stdout/stderr discipline for all functions used in command substitution:**

1. **All diagnostic output → stderr (`>&2`):** Progress messages, menus, prompts, confirmations, errors
2. **Only return values → stdout:** Region lists or single region names
3. **Interactive input from `/dev/tty`:** `read -rp "Select region: " choice </dev/tty` ensures prompts work when stdin is piped under azd hook execution
4. **Replace namerefs with indirect expansion:** `eval "local regions=(\"\${${regions_var}[@]}\"))"` for bash 3.2+ compatibility
5. **Explicit error handling:**
   - `trap 'echo "❌ ... failed at line $LINENO" >&2' ERR` after `set -euo pipefail`
   - Wrap each `azd env set` with `if ! azd env set ... ; then echo "❌ Failed..." >&2; exit 1; fi`
   - Final round-trip verification: `azd env get-value` after setting, exit 1 if mismatch
6. **Remove stale empty-string sets:** Deleted `azd env set AZURE_OPENAI_LOCATION_* ""` calls — setting empty doesn't unset

### Impact

- **Persistent regions:** `azd env set` now receives clean single-line values → persistence works
- **User sees prompts:** Menu output goes to stderr → displayed to user instead of captured
- **Silent failures eliminated:** ERR trap + explicit checks + round-trip verification
- **Portable:** bash 3.2+ compatible (macOS system bash)

### Migration

**No state to clear** — env vars were never written. Just re-run `azd up`. The picker will now display menus correctly and persist selections.

### Lessons Learned

1. **Command substitution capture discipline:** Functions used in `$(...)` or `< <(...)` must treat stdout as a return channel ONLY. All human-facing output must go to stderr.
2. **Interactive input under hooks:** `read </dev/tty` is mandatory when script may run with piped stdin.
3. **Nameref portability:** Avoid `local -n` in portable shell scripts. Use indirect expansion via `eval` for bash 3.2+ compatibility.
4. **Persistence verification:** Never assume `azd env set` succeeded. Always read back with `azd env get-value` and verify match.
5. **Error visibility:** ERR trap + explicit checks + actionable error messages prevent silent failures.

### Related

- `.squad/skills/azd-quota-aware-region-selection/SKILL.md` — added "Pitfalls" section documenting these issues
- Quota dimension fix (2026-05-20) — prior fix that made region selection accurate
- Deployment parameter orchestrator (2026-05-19) — same stdout discipline pattern applies

---

## Redfoot — Archive sandbox-dynamic-sessions OpenSpec Change

**Author:** Redfoot (Spec Manager)  
**Date:** 2026-05-27  
**Status:** Decided  
**Context:** Post-implementation archive of completed sandbox pool modernization  
**Commit:** ee82ae7 (`docs(openspec): archive sandbox-dynamic-sessions; update open-source-project status`)

### Decision

Archive the `sandbox-dynamic-sessions` OpenSpec change to `openspec/changes/archive/2026-05-27-sandbox-dynamic-sessions/` after full implementation verification and production deployment.

### Rationale

1. **Implementation Complete**: 49/50 core tasks done. Task 7.1 (cleanup-aci-orphans.sh) marked optional post-migration utility.
   - Session pool Bicep module + wiring deployed and tested
   - SessionSandboxClient (19/19 unit tests pass)
   - ACI infrastructure deleted
   - Backend test suite: 111 passed, no regressions
   - Docs updated (AGENTS.md, proposal.md)

2. **Production Verified**: Pascal confirmed end-to-end deployment in production.
   - Session allocation: subsecond (vs 30–120s ACI prior)
   - SSE streaming, task completion, session cleanup all working

3. **Spec Deltas Merged**: All capability specs updated and new specs created.
   - Modified: aci-sandbox-infra, aci-sandbox-lifecycle, copilot-cli-sandbox, sandbox-auth, sandbox-skill-mount
   - New: dynamic-session-sandbox, session-pool-infra
   - Deltas integrated into `openspec/specs/` (canonical library)

### Archive Location

`openspec/changes/archive/2026-05-27-sandbox-dynamic-sessions/`

Contains:
- proposal.md (with Post-Implementation Notes)
- design.md
- tasks.md (49/50 tasks checked)
- specs/ (historical delta snapshots)

### Remaining Work

**open-source-project** change: NOT archived.
- Sections 1–10, 12 complete (OSS docs, governance, decommission)
- Sections 11, 13–15 in progress (validation wave: fresh deploy, publish)
- Target: archive after validation passes

### Follow-Up

1. Cleanup-aci-orphans.sh can be written on-demand if legacy ACI groups discovered post-migration
2. Session pool observability (App Insights wiring) can be added as future enhancement
3. Consider documenting session pool scaling patterns as the feature matures
