# Skill: Quota-Aware Region Selection for azd

**Category:** Azure Developer CLI (azd) · Infrastructure as Code · Deployment Automation  
**Created:** 2026-05-19  
**Author:** Verbal  
**Updated:** 2026-05-19 (generalized to "Idempotent Parameter Collection")

## Summary

A reusable pattern for implementing idempotent, interactive parameter collection in `azd` preprovision hooks. Queries Azure APIs to discover resource availability and quota (or other metadata), then prompts users to select options or accepts auto-discovered values. Fully idempotent — safe to run multiple times, only prompts once per parameter.

Originally implemented for quota-aware region selection (OpenAI models), then generalized for ALL deployment parameters (subscription, tenant, custom domain, etc.).

## When to Use

Use this pattern when:
- Your `azd` template requires parameters that can be auto-discovered from Azure CLI or other sources
- You want to avoid manual `azd env set` cheatsheets in your README
- You need an interactive first-run experience that guides users to valid options
- You want to support both interactive (local) and non-interactive (CI/CD) deployment modes
- You want idempotency — subsequent runs reuse saved values without re-prompting

## Pattern Overview

1. **Preprovision Hook**: Create a bash script in `infra/scripts/` and wire it into `azure.yaml` preprovision hooks
2. **Check Existing Value**: Use `azd env get-value <PARAM_NAME>` to check if value is already set (idempotent)
3. **Auto-Discover**: Try to auto-discover the value from Azure CLI or other sources
4. **Interactive Prompt**: If not set and not discoverable, prompt user (only if interactive TTY)
5. **Store Value**: Save via `azd env set <PARAM_NAME> <value>` so Bicep can consume it
6. **Non-interactive Guard**: Fail fast with clear error if running in CI without pre-set values

## Implementation Example

### 1. Create the Parameter Collection Script

**File:** `infra/scripts/collect-<resource>-params.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}

check_az_login() {
    if ! az account show &>/dev/null; then
        echo "❌ Error: not logged in to Azure CLI"
        exit 1
    fi
}

# ──────────────────────────────────────────────────────────────────
# Example: Collect Azure Subscription ID
# ──────────────────────────────────────────────────────────────────
collect_subscription() {
    local sub_id
    
    # 1. Check if already set (idempotent)
    sub_id=$(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null || echo "")
    if [ -n "$sub_id" ]; then
        echo "✅ Subscription: $sub_id (from azd env)"
        return 0
    fi
    
    # 2. Auto-discover from Azure CLI
    sub_id=$(az account show --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$sub_id" ]; then
        azd env set AZURE_SUBSCRIPTION_ID "$sub_id"
        echo "✅ Subscription: $sub_id (auto-discovered)"
        return 0
    fi
    
    # 3. Interactive prompt (only if TTY)
    if is_noninteractive; then
        echo "❌ Error: running in non-interactive mode but AZURE_SUBSCRIPTION_ID not set"
        exit 1
    fi
    
    # List subscriptions and prompt
    local subs
    subs=$(az account list --query "[].{name:name, id:id}" -o tsv)
    echo "Available subscriptions:"
    local idx=1
    while IFS=$'\t' read -r name id; do
        echo "  $idx. $name ($id)"
        ((idx++))
    done <<< "$subs"
    
    read -rp "Select subscription [1]: " choice
    choice=${choice:-1}
    sub_id=$(echo "$subs" | sed -n "${choice}p" | awk '{print $NF}')
    
    # 4. Persist
    azd env set AZURE_SUBSCRIPTION_ID "$sub_id"
    echo "✅ Subscription: $sub_id"
}

# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
main() {
    check_az_login
    collect_subscription
    # ... collect other params
}

main "$@"
```

### 2. Wire into azure.yaml

```yaml
hooks:
  preprovision:
    shell: sh
    run: |
      bash infra/scripts/collect-<resource>-params.sh
      # Other preprovision tasks...

pipeline:
  variables:
    - AZURE_SUBSCRIPTION_ID
```

### 3. Parameterize Bicep

**`infra/main.bicep`:**
```bicep
@description('Azure subscription ID')
param subscriptionId string

module myResource 'modules/my-resource.bicep' = {
  name: 'my-resource'
  params: {
    subscriptionId: subscriptionId
  }
}
```

**`infra/main.parameters.json`:**
```json
{
  "parameters": {
    "subscriptionId": { "value": "${AZURE_SUBSCRIPTION_ID}" }
  }
}
```

### 4. Update README

Document the automatic behavior:

```markdown
## Deployment

Run `azd up`. On first run, the preprovision hooks will auto-discover your Azure subscription, tenant, and other parameters. Any missing values will be prompted once. All parameters are saved to the azd environment and reused on subsequent runs.

To override a parameter:
```bash
azd env set <PARAM_NAME> <value>
azd up
```

For CI/CD, pre-set required parameters:
```bash
azd env set AZURE_SUBSCRIPTION_ID <subscription-id>
```
```

## Key Techniques

### Idempotency Pattern

**ALWAYS check if the value is already set first:**
```bash
VALUE=$(azd env get-value PARAM_NAME 2>/dev/null || echo "")
if [ -n "$VALUE" ]; then
    echo "✅ Already configured: $VALUE"
    return 0
fi
```

### Auto-Discovery Sources

**Azure subscription:**
```bash
az account show --query id -o tsv
```

**Azure tenant:**
```bash
az account show --query tenantId -o tsv
```

**Signed-in user object ID:**
```bash
az ad signed-in-user show --query id -o tsv
```

**Resource availability (e.g., AI models):**
```bash
az cognitiveservices model list --location <region> \
    --query "[?name=='<model>'].name" -o tsv
```

**Quota checking (EXACT per-model dimension):**

⚠️ **CRITICAL:** Azure quota is per-model, not per-SKU. Always check the exact dimension `OpenAI.<SKU>.<model-name>`.

```bash
# Quota dimension format: OpenAI.<SKU>.<model-name>
# Example: OpenAI.GlobalStandard.gpt-realtime
QUOTA_DIMENSION="OpenAI.GlobalStandard.${model_name}"

az cognitiveservices usage list --location <region> \
    --query "[?name.value=='$QUOTA_DIMENSION'].{current: currentValue, limit: limit}" -o json
```

Parse JSON in bash using Python (check if available >= required):
```bash
python3 -c "
import sys, json
required = int('$required_capacity')
try:
    data = json.load(sys.stdin)
    if len(data) > 0:
        item = data[0]
        limit = item.get('limit', 0)
        current = item.get('current', 0)
        available = limit - current
        if available >= required:
            print('true')
            sys.exit(0)
    print('false')
except:
    print('false')
"
```

**Key learnings:**
- Each model (gpt-5.2, gpt-realtime, o3-deep-research, etc.) has its own quota dimension
- A region may have quota for gpt-5.2 but NOT gpt-realtime — check EVERY model in a group
- Quota dimension must exist (even with limit=0) for model to be deployable in that region
- Required capacity varies by model: gpt-5.2=500, gpt-realtime=10, o3-deep-research=1500 (from Bicep)
- Use parallel arrays for models + capacities to maintain alignment

### Non-interactive Detection

```bash
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}
```

### Secure Secret Handling

Use `azd env set --secret` for sensitive values (if supported):
```bash
if azd env set --help 2>&1 | grep -q -- '--secret'; then
    azd env set --secret ENTRA_CLIENT_SECRET "$secret"
else
    azd env set ENTRA_CLIENT_SECRET "$secret"
fi
```

## Best Practices

1. **Check azd env FIRST** — always use `azd env get-value` before prompting or discovering
2. **Auto-discover when possible** — prefer `az account show` over prompts
3. **Prompt only if interactive** — guard all prompts with `is_noninteractive()` check
4. **Fail fast in CI** — if required var is missing in non-interactive mode, exit 1 with clear error listing what's needed
5. **Persist immediately** — call `azd env set` as soon as you have a value
6. **Actionable errors** — if no valid options, tell user how to fix (e.g., request quota, override manually)
7. **Summary output** — print a summary at the end showing resolved values (mask secrets)
8. **Validate syntax** — always run `bash -n <script>` before committing

## Gotchas

- **Subscription context**: Some `az` commands require `--subscription` flag if you haven't run `az account set`
- **Service principal auth**: `az ad signed-in-user show` fails if running as service principal (CI) — handle gracefully with fallback to empty
- **Empty strings are valid**: For optional params, persisting an empty string (`azd env set PARAM ""`) is valid and prevents re-prompting
- **azd env get-value exit codes**: Non-existent vars return exit code 1, so use `|| echo ""` to handle

## Testing

1. **Syntax check**: `bash -n infra/scripts/<script>.sh`
2. **Bicep compilation**: `az bicep build --file infra/main.bicep`
3. **JSON/YAML validation**: `python3 -m json.tool <file>.json`
4. **Non-interactive mode**: `echo "" | bash infra/scripts/<script>.sh` (should fail with clear error)
5. **Idempotency**: Run twice — second run should skip all prompts

## Example Use Cases

### Deployment Parameters (General)
- Subscription, tenant, location selection
- Custom domain configuration
- RBAC principal assignment
- Feature flags (e.g., enable/disable components)

### Resource-Specific Parameters
- **OpenAI model deployments** (varying quota by region)
- **GPU VM families** (limited regional availability)
- **High-SKU databases** (quota-constrained)
- **Preview features** (only available in specific regions)

## Real-World Implementation: Turbo Voice Agent

This pattern is used in two preprovision scripts:

1. **`collect-deployment-params.sh`** — collects 8 deployment parameters:
   - `AZURE_SUBSCRIPTION_ID` (auto-discover or prompt if multiple)
   - `AZURE_LOCATION` (usually set by azd, fallback prompt)
   - `ENTRA_TENANT_ID` (auto-discover, never prompt)
   - `CUSTOM_DOMAIN_NAME` (prompt once, optional)
   - `EXISTING_CERT_NAME` (prompt if custom domain set, optional)
   - `ENTRA_CLIENT_SECRET` (prompt once with explanation, optional)
   - `DEPLOYER_PRINCIPAL_ID` (auto-discover, fallback to empty if service principal)
   - `DEPLOY_RBAC` (default to `true`, never prompt)

2. **`select-model-regions.sh`** — collects 3 region parameters:
   - Queries Azure for AI model availability and quota
   - Presents numbered list of viable regions
   - Stores user selections as `AZURE_OPENAI_LOCATION_PRIMARY/VOICE/RESEARCH`

Both scripts follow the same pattern: check azd env → auto-discover → prompt → persist.

## Related Patterns

- **azd preprovision hooks**: https://learn.microsoft.com/azure/developer/azure-developer-cli/azd-extensibility
- **Azure CLI scripting**: https://learn.microsoft.com/cli/azure/script-az-cli-bash
- **Bicep parameter substitution**: https://learn.microsoft.com/azure/azure-resource-manager/bicep/parameters

## Maintainability

This pattern scales well:
- **Multiple resource types**: create one script per logical group
- **Multiple params per script**: one script can collect multiple related params
- **Shared helper functions**: extract `is_noninteractive()`, `check_az_login()`, etc. into a sourced library if you have many scripts
- **Preprovision hook order**: run general param collection FIRST, then resource-specific scripts (e.g., `collect-deployment-params.sh` → `select-model-regions.sh` → `setup-entra-app.sh`)


## Implementation Example

### 1. Create the Selection Script

**File:** `infra/scripts/select-<resource>-regions.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Check if running in non-interactive mode
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}

# Verify Azure CLI is logged in
check_az_login() {
    if ! az account show &>/dev/null; then
        echo "❌ Error: not logged in to Azure CLI"
        exit 1
    fi
}

# Query resource availability in a region
is_resource_available() {
    local region=$1
    local resource_name=$2
    # Example: az cognitiveservices model list --location "$region"
    # Parse output to check if resource exists
}

# Check if region has remaining quota
has_quota() {
    local region=$1
    # Example: az cognitiveservices usage list --location "$region"
    # Parse JSON: currentValue < limit
}

# Find regions where resource is available AND has quota
find_available_regions() {
    local available_regions=()
    for region in "${CANDIDATE_REGIONS[@]}"; do
        if is_resource_available "$region" && has_quota "$region"; then
            available_regions+=("$region")
        fi
    done
    echo "${available_regions[@]}"
}

# Interactive picker
pick_region() {
    local group_name=$1
    local -n regions=$2
    
    if [ ${#regions[@]} -eq 0 ]; then
        echo "❌ No regions with availability and quota"
        exit 1
    fi
    
    echo "Available regions for $group_name:"
    for i in "${!regions[@]}"; do
        echo "  $((i + 1)). ${regions[$i]}"
    done
    
    read -rp "Select region: " choice
    echo "${regions[$((choice - 1))]}"
}

# Main logic
main() {
    check_az_login
    
    # Non-interactive mode check
    if is_noninteractive; then
        REGION=$(azd env get-value AZURE_RESOURCE_LOCATION 2>/dev/null || echo "")
        if [ -z "$REGION" ]; then
            echo "❌ Error: running in non-interactive mode but AZURE_RESOURCE_LOCATION not set"
            echo "   azd env set AZURE_RESOURCE_LOCATION <region>"
            exit 1
        fi
        exit 0
    fi
    
    # Idempotency: skip if already set
    REGION=$(azd env get-value AZURE_RESOURCE_LOCATION 2>/dev/null || echo "")
    if [ -n "$REGION" ]; then
        echo "✅ Region already configured: $REGION"
        exit 0
    fi
    
    # Interactive selection
    readarray -t available < <(find_available_regions)
    REGION=$(pick_region "RESOURCE" available)
    azd env set AZURE_RESOURCE_LOCATION "$REGION"
    
    echo "✅ Selected: $REGION"
}

main "$@"
```

### 2. Wire into azure.yaml

```yaml
hooks:
  preprovision:
    shell: sh
    run: |
      bash infra/scripts/select-<resource>-regions.sh
      # Other preprovision tasks...

pipeline:
  variables:
    - AZURE_RESOURCE_LOCATION
```

### 3. Parameterize Bicep

**`infra/main.bicep`:**
```bicep
@description('Azure region for <resource>')
param resourceLocation string = 'eastus'

module myResource 'modules/my-resource.bicep' = {
  name: 'my-resource'
  params: {
    location: resourceLocation
  }
}
```

**`infra/main.parameters.json`:**
```json
{
  "parameters": {
    "resourceLocation": { "value": "${AZURE_RESOURCE_LOCATION=eastus}" }
  }
}
```

### 4. Update README

Document the interactive behavior and CI requirements:

```markdown
## Deployment

On first run, `azd up` will prompt you to select a region for <resource> based on availability and quota in your subscription. Your selection is stored and reused on subsequent runs.

For CI/CD, pre-set the region:
```bash
azd env set AZURE_RESOURCE_LOCATION <region>
```

## Key Techniques

### Availability Detection

**Cognitive Services models:**
```bash
az cognitiveservices model list --location <region> \
    --query "[?name=='<model>'].name" -o tsv
```

**VM SKUs:**
```bash
az vm list-skus --location <region> \
    --query "[?name=='<sku>'].name" -o tsv
```

### Quota Checking

**Cognitive Services:**
```bash
az cognitiveservices usage list --location <region> \
    --query "[?contains(name.value, 'OpenAI.Standard')].{current: currentValue, limit: limit}" -o json
```

Parse JSON in bash using Python:
```bash
python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    if item.get('limit', 0) > item.get('current', 0):
        print('true')
        sys.exit(0)
print('false')
"
```

**Compute:**
```bash
az vm list-usage --location <region> \
    --query "[?name.value=='<family>'].{current: currentValue, limit: limit}" -o json
```

### Non-interactive Detection

```bash
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}
```

### Idempotency

Always check if the env var is already set:
```bash
VALUE=$(azd env get-value ENV_VAR_NAME 2>/dev/null || echo "")
if [ -n "$VALUE" ]; then
    echo "✅ Already configured: $VALUE"
    exit 0
fi
```

## Best Practices

1. **Run region selection FIRST in preprovision** — it's the fastest-failing check
2. **Print progress messages** — quota queries can take 5-10 seconds per region
3. **Mark defaults** — if a region matches the hardcoded default, show it in the list
4. **Conservative quota check** — if API doesn't give per-resource quota, check aggregate
5. **Actionable errors** — if no regions with quota, tell user how to request more or override
6. **Validate syntax** — always run `bash -n <script>` before committing

## Gotchas

- **Quota API granularity**: Some Azure quota APIs report aggregate limits (e.g., "OpenAI.Standard"), not per-model. Use conservative heuristics.
- **Slow API calls**: Querying 14 candidate regions can take 30-60 seconds. Only query when env var is NOT set.
- **Regional variations**: Some models (e.g., o3-deep-research) are only in 2-3 regions globally. Use a broad candidate list.
- **CI requires pre-set vars**: GitHub Actions runs with no TTY, so env vars MUST be set via repository variables or `azd env set` before `azd up`.

## Testing

1. **Syntax check**: `bash -n infra/scripts/<script>.sh`
2. **Bicep compilation**: `az bicep build --file infra/main.bicep`
3. **JSON/YAML validation**: `python3 -m json.tool <file>.json`
4. **Non-interactive mode**: `echo "" | bash infra/scripts/<script>.sh` (should fail with clear error)
5. **Idempotency**: Run twice — second run should skip prompt

## Example Use Cases

- **OpenAI model deployments** (varying quota by region)
- **GPU VM families** (limited regional availability)
- **High-SKU databases** (quota-constrained)
- **Preview features** (only available in specific regions)

## Related Patterns

- **azd preprovision hooks**: https://learn.microsoft.com/azure/developer/azure-developer-cli/azd-extensibility
- **Azure CLI scripting**: https://learn.microsoft.com/cli/azure/script-az-cli-bash
- **Bicep parameter substitution**: https://learn.microsoft.com/azure/azure-resource-manager/bicep/parameters

## Maintainability

This pattern scales well:
- Multiple resource types: create one script per logical group (e.g., `select-openai-regions.sh`, `select-gpu-regions.sh`)
- Multiple env vars: one script can prompt for multiple related regions (see `select-model-regions.sh` for an example with 3 Foundry accounts)
- Shared helper functions: extract `is_noninteractive()`, `check_az_login()`, etc. into a sourced library if you have many scripts
