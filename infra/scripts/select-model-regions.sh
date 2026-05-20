#!/usr/bin/env bash
# Select Azure regions for OpenAI model deployments with quota awareness.
# Queries Azure for model availability and remaining quota across candidate regions.
# Stores user selections as azd env vars for Bicep consumption.
# Idempotent — skips prompts if env vars are already set.
set -euo pipefail

# ──────────────────────────────────────────────────────────────────
# Model Groups — each Foundry account hosts a group of models
# ──────────────────────────────────────────────────────────────────
PRIMARY_MODELS=("gpt-5.2" "gpt-4.1" "gpt-4o-transcribe")
VOICE_MODELS=("gpt-realtime")
RESEARCH_MODELS=("o3-deep-research")

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
    
    [ -n "$models" ]
}

# ──────────────────────────────────────────────────────────────────
# Helper: check if a region has remaining quota for a model deployment
# Uses az cognitiveservices usage list to fetch quota limits and current usage
# Returns 0 if quota available, 1 otherwise
# ──────────────────────────────────────────────────────────────────
has_quota() {
    local region=$1
    local model_name=$2
    
    # Query usage for OpenAI deployments in the region
    # Schema: { name: { value: "OpenAI.Standard.<model>" }, currentValue: X, limit: Y }
    # For GlobalStandard SKU, check OpenAI.Standard.* quota
    local usage=$(az cognitiveservices usage list \
        --location "$region" \
        --query "[?contains(name.value, 'OpenAI.Standard')].{current: currentValue, limit: limit}" \
        -o json 2>/dev/null || echo "[]")
    
    # If usage query failed or returned empty, assume no quota available
    if [ "$usage" = "[]" ] || [ -z "$usage" ]; then
        return 1
    fi
    
    # Parse quota — we consider quota available if ANY OpenAI.Standard resource has remaining quota
    # This is a conservative check; in practice, each model has its own quota dimension
    local has_remaining=$(echo "$usage" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data:
        if item.get('limit', 0) > item.get('current', 0):
            print('true')
            sys.exit(0)
    print('false')
except:
    print('false')
" 2>/dev/null || echo "false")
    
    [ "$has_remaining" = "true" ]
}

# ──────────────────────────────────────────────────────────────────
# Find regions where ALL models in a group are available with quota
# ──────────────────────────────────────────────────────────────────
find_available_regions() {
    local -n models=$1  # nameref to model array
    local available_regions=()
    
    echo "Checking availability for: ${models[*]}"
    
    for region in "${CANDIDATE_REGIONS[@]}"; do
        local all_available=true
        
        for model in "${models[@]}"; do
            if ! is_model_available "$region" "$model"; then
                all_available=false
                break
            fi
        done
        
        # Only check quota if all models are available
        if [ "$all_available" = true ]; then
            # For quota check, we use the first model as a proxy
            # (quota is typically per-account, not per-model)
            if has_quota "$region" "${models[0]}"; then
                available_regions+=("$region")
            fi
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
    
    # Interactive mode — check if env vars are already set
    PRIMARY_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_PRIMARY 2>/dev/null || echo "")
    VOICE_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_VOICE 2>/dev/null || echo "")
    RESEARCH_LOC=$(azd env get-value AZURE_OPENAI_LOCATION_RESEARCH 2>/dev/null || echo "")
    
    # Skip prompt if all env vars are already set
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
        readarray -t primary_regions < <(find_available_regions PRIMARY_MODELS)
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
        readarray -t voice_regions < <(find_available_regions VOICE_MODELS)
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
        readarray -t research_regions < <(find_available_regions RESEARCH_MODELS)
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
