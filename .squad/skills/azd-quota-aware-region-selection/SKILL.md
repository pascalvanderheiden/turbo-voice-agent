# Skill: Quota-Aware Region Selection for azd

**Category:** Azure Developer CLI (azd) · Infrastructure as Code · Deployment Automation  
**Created:** 2026-05-19  
**Author:** Verbal

## Summary

A reusable pattern for implementing quota-aware, interactive region selection in `azd` preprovision hooks. Queries Azure APIs to discover resource availability and quota, then prompts users to select regions where resources can actually be deployed.

## When to Use

Use this pattern when:
- Your `azd` template deploys Azure resources with regional quota limits (e.g., OpenAI models, GPU VMs, high-SKU services)
- You want to avoid deployment failures due to hardcoded regions without quota
- You need an interactive first-run experience that guides users to regions that will work
- You want to support both interactive (local) and non-interactive (CI/CD) deployment modes

## Pattern Overview

1. **Preprovision Hook**: Create a bash script in `infra/scripts/` and wire it into `azure.yaml` preprovision hooks
2. **Query Availability**: Use Azure CLI to query which regions have the required resources available
3. **Check Quota**: Parse Azure usage APIs to determine remaining quota in each candidate region
4. **Interactive Selection**: Present a numbered list of viable regions, prompt user to pick
5. **Store Selection**: Save the user's choice via `azd env set` so Bicep can consume it
6. **Idempotency**: Skip prompts if the env var is already set (re-entrant `azd up`)
7. **Non-interactive Guard**: Fail fast with clear error if running in CI without pre-set env vars

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
