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
