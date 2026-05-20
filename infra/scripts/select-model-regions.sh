#!/usr/bin/env bash
# Select Azure regions for OpenAI model deployments with quota awareness.
# Queries Azure for model availability and remaining quota across candidate regions.
# Stores user selections as azd env vars for Bicep consumption.
# Idempotent — skips prompts if env vars are already set.
set -euo pipefail

# ──────────────────────────────────────────────────────────────────
# Model Groups — each Foundry account hosts a group of models
# Models and their required capacity (parallel arrays)
# ──────────────────────────────────────────────────────────────────
PRIMARY_MODELS=("gpt-5.2" "gpt-4.1" "gpt-4o-transcribe")
PRIMARY_CAPACITY=(500 500 200)

VOICE_MODELS=("gpt-realtime")
VOICE_CAPACITY=(10)

RESEARCH_MODELS=("o3-deep-research")
RESEARCH_CAPACITY=(1500)

# SKU name used for quota dimension lookups
# Quota dimension format: OpenAI.<SKU>.<model-name>
QUOTA_SKU="GlobalStandard"

# Candidate regions to query (well-known OpenAI regions)
CANDIDATE_REGIONS=(
    "eastus" "eastus2" "westus" "westus2" "westus3"
    "northcentralus" "southcentralus" "centralus"
    "swedencentral" "westeurope" "francecentral" "uksouth"
    "japaneast" "australiaeast"
)

# Current hardcoded defaults (fallback if region not found with quota)
DEFAULT_PRIMARY="eastus2"
DEFAULT_VOICE="centralus"
DEFAULT_RESEARCH="westus"

# ──────────────────────────────────────────────────────────────────
# Helper: check if running in non-interactive mode
# ──────────────────────────────────────────────────────────────────
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}

# ──────────────────────────────────────────────────────────────────
# Helper: check if Azure CLI is logged in and subscription is set
# ──────────────────────────────────────────────────────────────────
check_az_login() {
    if ! az account show &>/dev/null; then
        echo "❌ Error: not logged in to Azure CLI"
        echo "   Run: az login"
        exit 1
    fi

    SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || true)
    if [ -z "$SUBSCRIPTION_ID" ]; then
        echo "❌ Error: no Azure subscription set"
        echo "   Run: az account set --subscription <subscription-id>"
        exit 1
    fi

    echo "Using subscription: $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"
}

# ──────────────────────────────────────────────────────────────────
# Helper: check if a model is available in a region
# Uses az cognitiveservices model list to detect model availability
# Also verifies the quota dimension exists (even if exhausted) to confirm
# the model is actually deployable in the region
# ──────────────────────────────────────────────────────────────────
is_model_available() {
    local region=$1
    local model_name=$2
    
    # Query model list for the region — if model exists, it's available
    # Output is JSON array of model objects with { name, version, ... }
    local models=$(az cognitiveservices model list \
        --location "$region" \
        --query "[?name=='$model_name'].name" \
        -o tsv 2>/dev/null || echo "")
    
    if [ -z "$models" ]; then
        return 1
    fi
    
    # Also check that the quota dimension exists for this model
    # Dimension format: OpenAI.<SKU>.<model-name>
    local quota_dimension="OpenAI.${QUOTA_SKU}.${model_name}"
    local usage=$(az cognitiveservices usage list \
        --location "$region" \
        --query "[?name.value=='$quota_dimension'].limit" \
        -o tsv 2>/dev/null || echo "")
    
    # If quota dimension exists (even with limit 0), model is deployable
    [ -n "$usage" ]
}

# ──────────────────────────────────────────────────────────────────
# Helper: check if a region has sufficient quota for a specific model
# Uses exact quota dimension: OpenAI.<SKU>.<model-name>
# Returns 0 if (limit - current) >= required_capacity, 1 otherwise
# ──────────────────────────────────────────────────────────────────
has_quota_for_model() {
    local region=$1
    local model_name=$2
    local required_capacity=$3
    
    # Quota dimension format: OpenAI.<SKU>.<model-name>
    local quota_dimension="OpenAI.${QUOTA_SKU}.${model_name}"
    
    # Query usage for the exact quota dimension
    # Schema: { name: { value: "..." }, currentValue: X, limit: Y }
    local usage=$(az cognitiveservices usage list \
        --location "$region" \
        --query "[?name.value=='$quota_dimension'].{current: currentValue, limit: limit}" \
        -o json 2>/dev/null || echo "[]")
    
    # If usage query failed or returned empty, no quota available
    if [ "$usage" = "[]" ] || [ -z "$usage" ]; then
        return 1
    fi
    
    # Parse quota — check if (limit - current) >= required_capacity
    local has_sufficient=$(echo "$usage" | python3 -c "
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
" 2>/dev/null || echo "false")
    
    [ "$has_sufficient" = "true" ]
}

# ──────────────────────────────────────────────────────────────────
# Helper: get quota info for a model in a region (for verbose output)
# Returns JSON with {available, limit, current} or empty if quota dimension not found
# ──────────────────────────────────────────────────────────────────
get_quota_info() {
    local region=$1
    local model_name=$2
    
    local quota_dimension="OpenAI.${QUOTA_SKU}.${model_name}"
    
    local usage=$(az cognitiveservices usage list \
        --location "$region" \
        --query "[?name.value=='$quota_dimension'].{current: currentValue, limit: limit}" \
        -o json 2>/dev/null || echo "[]")
    
    if [ "$usage" = "[]" ] || [ -z "$usage" ]; then
        echo ""
        return
    fi
    
    # Extract quota values
    echo "$usage" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if len(data) > 0:
        item = data[0]
        limit = item.get('limit', 0)
        current = item.get('current', 0)
        available = limit - current
        print(json.dumps({'available': available, 'limit': limit, 'current': current}))
    else:
        print('')
except:
    print('')
" 2>/dev/null || echo ""
}

# ──────────────────────────────────────────────────────────────────
# Find regions where ALL models in a group are available with quota
# Checks exact quota dimensions per model: OpenAI.<SKU>.<model-name>
# Verbose output shows per-region per-model availability + quota
# ──────────────────────────────────────────────────────────────────
find_available_regions() {
    local -n models=$1       # nameref to model array
    local -n capacities=$2   # nameref to capacity array
    local available_regions=()
    
    echo ""
    echo "Checking availability for: ${models[*]}"
    echo ""
    
    for region in "${CANDIDATE_REGIONS[@]}"; do
        local all_ok=true
        local region_output=""
        
        # Check each model in the group
        for i in "${!models[@]}"; do
            local model="${models[$i]}"
            local required="${capacities[$i]}"
            
            # Check model availability (model list + quota dimension exists)
            if ! is_model_available "$region" "$model"; then
                region_output+="    ✗ ${model} — not available in region\n"
                all_ok=false
                continue
            fi
            
            # Check quota
            local quota_info=$(get_quota_info "$region" "$model")
            if [ -n "$quota_info" ]; then
                local available=$(echo "$quota_info" | python3 -c "import sys, json; print(json.load(sys.stdin).get('available', 0))" 2>/dev/null || echo "0")
                local limit=$(echo "$quota_info" | python3 -c "import sys, json; print(json.load(sys.stdin).get('limit', 0))" 2>/dev/null || echo "0")
                
                if has_quota_for_model "$region" "$model" "$required"; then
                    region_output+="    ✓ ${model} — quota ${available}/${limit} available (need ${required})\n"
                else
                    region_output+="    ✗ ${model} — quota ${available}/${limit} available (need ${required})\n"
                    all_ok=false
                fi
            else
                region_output+="    ✗ ${model} — no quota dimension found\n"
                all_ok=false
            fi
        done
        
        # Print region summary
        if [ "$all_ok" = true ]; then
            echo -e "  Region $region:"
            echo -e "$region_output"
            available_regions+=("$region")
        else
            echo -e "  Region $region: SKIP"
            echo -e "$region_output"
        fi
    done
    
    echo "${available_regions[@]}"
}

# ──────────────────────────────────────────────────────────────────
# Interactive region picker
# ──────────────────────────────────────────────────────────────────
pick_region() {
    local group_name=$1
    local -n regions=$2  # nameref to available regions array
    local default_region=$3
    
    if [ ${#regions[@]} -eq 0 ]; then
        echo ""
        echo "❌ No regions found with availability and quota for $group_name models"
        echo "   Possible actions:"
        echo "   1. Request quota increase in Azure Portal for OpenAI Standard deployments"
        echo "   2. Manually set the env var and provision in a region you know has quota:"
        echo "      azd env set AZURE_OPENAI_LOCATION_${group_name^^} <region>"
        echo ""
        exit 1
    fi
    
    echo ""
    echo "Available regions for $group_name (with quota):"
    echo ""
    
    local default_idx=""
    for i in "${!regions[@]}"; do
        local marker=""
        if [ "${regions[$i]}" = "$default_region" ]; then
            marker=" (current default)"
            default_idx=$((i + 1))
        fi
        echo "  $((i + 1)). ${regions[$i]}$marker"
    done
    
    echo ""
    if [ -n "$default_idx" ]; then
        read -rp "Select region for $group_name [$default_idx]: " choice
        choice=${choice:-$default_idx}
    else
        read -rp "Select region for $group_name: " choice
    fi
    
    # Validate choice
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#regions[@]}" ]; then
        echo "❌ Invalid selection"
        exit 1
    fi
    
    local selected="${regions[$((choice - 1))]}"
    echo "✅ Selected: $selected"
    echo "$selected"
}

# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
main() {
    echo "=== Azure OpenAI Model Region Selection ==="
    echo ""
    
    # Check Azure CLI login
    check_az_login
    
    # Check if running in non-interactive mode
    if is_noninteractive; then
        # Non-interactive mode requires all env vars to be pre-set
        PRIMARY_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_PRIMARY 2>/dev/null || echo "")
        VOICE_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_VOICE 2>/dev/null || echo "")
        RESEARCH_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_RESEARCH 2>/dev/null || echo "")
        
        if [ -z "$PRIMARY_LOC" ] || [ -z "$VOICE_LOC" ] || [ -z "$RESEARCH_LOC" ]; then
            echo "❌ Error: running in non-interactive mode (CI) but required env vars not set"
            echo ""
            echo "   Set these environment variables before running azd up:"
            echo "   - AZURE_OPENAI_LOCATION_PRIMARY"
            echo "   - AZURE_OPENAI_LOCATION_VOICE"
            echo "   - AZURE_OPENAI_LOCATION_RESEARCH"
            echo ""
            echo "   Example:"
            echo "     azd env set AZURE_OPENAI_LOCATION_PRIMARY eastus2"
            echo "     azd env set AZURE_OPENAI_LOCATION_VOICE centralus"
            echo "     azd env set AZURE_OPENAI_LOCATION_RESEARCH westus"
            echo ""
            exit 1
        fi
        
        echo "Non-interactive mode: using pre-set regions"
        echo "  Primary:  $PRIMARY_LOC"
        echo "  Voice:    $VOICE_LOC"
        echo "  Research: $RESEARCH_LOC"
        echo ""
        exit 0
    fi
    
    # Interactive mode — check if env vars are already set and validate them
    PRIMARY_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_PRIMARY 2>/dev/null || echo "")
    VOICE_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_VOICE 2>/dev/null || echo "")
    RESEARCH_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_RESEARCH 2>/dev/null || echo "")
    
    # Validate existing env vars against quota
    # If any region no longer has quota for its models, clear it and re-prompt
    if [ -n "$PRIMARY_LOC" ]; then
        local primary_valid=true
        for i in "${!PRIMARY_MODELS[@]}"; do
            if ! has_quota_for_model "$PRIMARY_LOC" "${PRIMARY_MODELS[$i]}" "${PRIMARY_CAPACITY[$i]}"; then
                echo "⚠️  Warning: Previously selected PRIMARY region ($PRIMARY_LOC) no longer has quota for ${PRIMARY_MODELS[$i]}"
                echo "   Clearing AZURE_OPENAI_LOCATION_PRIMARY — you will be re-prompted"
                echo ""
                azd env set AZURE_OPENAI_LOCATION_PRIMARY ""
                PRIMARY_LOC=""
                primary_valid=false
                break
            fi
        done
    fi
    
    if [ -n "$VOICE_LOC" ]; then
        local voice_valid=true
        for i in "${!VOICE_MODELS[@]}"; do
            if ! has_quota_for_model "$VOICE_LOC" "${VOICE_MODELS[$i]}" "${VOICE_CAPACITY[$i]}"; then
                echo "⚠️  Warning: Previously selected VOICE region ($VOICE_LOC) no longer has quota for ${VOICE_MODELS[$i]}"
                echo "   Clearing AZURE_OPENAI_LOCATION_VOICE — you will be re-prompted"
                echo ""
                azd env set AZURE_OPENAI_LOCATION_VOICE ""
                VOICE_LOC=""
                voice_valid=false
                break
            fi
        done
    fi
    
    if [ -n "$RESEARCH_LOC" ]; then
        local research_valid=true
        for i in "${!RESEARCH_MODELS[@]}"; do
            if ! has_quota_for_model "$RESEARCH_LOC" "${RESEARCH_MODELS[$i]}" "${RESEARCH_CAPACITY[$i]}"; then
                echo "⚠️  Warning: Previously selected RESEARCH region ($RESEARCH_LOC) no longer has quota for ${RESEARCH_MODELS[$i]}"
                echo "   Clearing AZURE_OPENAI_LOCATION_RESEARCH — you will be re-prompted"
                echo ""
                azd env set AZURE_OPENAI_LOCATION_RESEARCH ""
                RESEARCH_LOC=""
                research_valid=false
                break
            fi
        done
    fi
    
    # Skip prompt if all env vars are set and still valid
    if [ -n "$PRIMARY_LOC" ] && [ -n "$VOICE_LOC" ] && [ -n "$RESEARCH_LOC" ]; then
        echo "✅ Model regions already configured:"
        echo "   Primary:  $PRIMARY_LOC"
        echo "   Voice:    $VOICE_LOC"
        echo "   Research: $RESEARCH_LOC"
        echo ""
        echo "To re-select regions, unset the env vars first:"
        echo "  azd env set AZURE_OPENAI_LOCATION_PRIMARY ''"
        echo "  azd env set AZURE_OPENAI_LOCATION_VOICE ''"
        echo "  azd env set AZURE_OPENAI_LOCATION_RESEARCH ''"
        echo ""
        exit 0
    fi
    
    # ────────────────────────────────────────────────────────────
    # Primary Foundry (gpt-5.2, gpt-4.1, gpt-4o-transcribe)
    # ────────────────────────────────────────────────────────────
    if [ -z "$PRIMARY_LOC" ]; then
        echo "Scanning for Primary Foundry regions (gpt-5.2, gpt-4.1, gpt-4o-transcribe)..."
        readarray -t primary_regions < <(find_available_regions PRIMARY_MODELS PRIMARY_CAPACITY)
        PRIMARY_LOC=$(pick_region "PRIMARY" primary_regions "$DEFAULT_PRIMARY")
        azd env set AZURE_OPENAI_LOCATION_PRIMARY "$PRIMARY_LOC"
    else
        echo "✅ Primary region already set: $PRIMARY_LOC"
    fi
    
    # ────────────────────────────────────────────────────────────
    # Voice Foundry (gpt-realtime)
    # ────────────────────────────────────────────────────────────
    if [ -z "$VOICE_LOC" ]; then
        echo ""
        echo "Scanning for Voice Foundry regions (gpt-realtime)..."
        readarray -t voice_regions < <(find_available_regions VOICE_MODELS VOICE_CAPACITY)
        VOICE_LOC=$(pick_region "VOICE" voice_regions "$DEFAULT_VOICE")
        azd env set AZURE_OPENAI_LOCATION_VOICE "$VOICE_LOC"
    else
        echo "✅ Voice region already set: $VOICE_LOC"
    fi
    
    # ────────────────────────────────────────────────────────────
    # Research Foundry (o3-deep-research)
    # ────────────────────────────────────────────────────────────
    if [ -z "$RESEARCH_LOC" ]; then
        echo ""
        echo "Scanning for Research Foundry regions (o3-deep-research)..."
        readarray -t research_regions < <(find_available_regions RESEARCH_MODELS RESEARCH_CAPACITY)
        RESEARCH_LOC=$(pick_region "RESEARCH" research_regions "$DEFAULT_RESEARCH")
        azd env set AZURE_OPENAI_LOCATION_RESEARCH "$RESEARCH_LOC"
    else
        echo "✅ Research region already set: $RESEARCH_LOC"
    fi
    
    # ────────────────────────────────────────────────────────────
    # Summary
    # ────────────────────────────────────────────────────────────
    echo ""
    echo "=== Region Selection Complete ==="
    echo "  Primary:  $PRIMARY_LOC (gpt-5.2, gpt-4.1, gpt-4o-transcribe)"
    echo "  Voice:    $VOICE_LOC (gpt-realtime)"
    echo "  Research: $RESEARCH_LOC (o3-deep-research)"
    echo ""
    echo "Stored in azd environment. Proceeding with deployment..."
    echo ""
}

main "$@"
