#!/usr/bin/env bash
# Select Azure regions for OpenAI model deployments with quota awareness.
# Queries Azure for model availability and remaining quota across candidate regions.
# Stores user selections as azd env vars for Bicep consumption.
# Idempotent — skips prompts if env vars are already set.
set -euo pipefail
trap 'echo "❌ select-model-regions.sh failed at line $LINENO (exit $?)" >&2' ERR

# ──────────────────────────────────────────────────────────────────
# Helper: safely read an azd env variable (never prints errors to stdout)
# Usage: get_azd_env VAR_NAME  -> echoes value or empty string
# ──────────────────────────────────────────────────────────────────
get_azd_env() {
    (azd env get-values 2>/dev/null || true) | awk -F= -v key="$1" '
        $1 == key {
            value = substr($0, index($0, "=") + 1)
            gsub(/^"|"$/, "", value)
            print value
        }
        END { exit 0 }
    '
}

has_azd_env() {
    (azd env get-values 2>/dev/null || true) | awk -F= -v key="$1" '
        $1 == key { found = 1 }
        END { exit found ? 0 : 1 }
    '
}

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
        echo "❌ Error: not logged in to Azure CLI" >&2
        echo "   Run: az login" >&2
        exit 1
    fi

    SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || true)
    if [ -z "$SUBSCRIPTION_ID" ]; then
        echo "❌ Error: no Azure subscription set" >&2
        echo "   Run: az account set --subscription <subscription-id>" >&2
        exit 1
    fi

    echo "Using subscription: $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)" >&2
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
    
    # The model list API returns names like "OpenAI.gpt-5.2.2025-12-11" (not bare model name).
    # Use contains() match. If any entry matches the model name substring, it's listed.
    local models
    models=$(az cognitiveservices model list \
        --location "$region" \
        --query "[?contains(name,'$model_name')].name" \
        -o tsv 2>/dev/null || echo "")

    if [ -z "$models" ]; then
        return 1
    fi

    # Model list is the deployability signal. Some models do not expose a matching
    # GlobalStandard quota dimension even though deployment preflight accepts them.
    return 0
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
    local has_sufficient
    has_sufficient=$(echo "$usage" | python3 -c "
import sys, json
required = int('$required_capacity')
try:
    data = json.load(sys.stdin)
    if len(data) > 0:
        item = data[0]
        limit = item.get('limit', 0)
        current = item.get('current', 0)
        available = limit - current
        print('true' if available >= required else 'false')
    else:
        print('false')
except Exception:
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
# ALL diagnostic output goes to stderr; stdout contains ONLY the space-separated region list
# ──────────────────────────────────────────────────────────────────
find_available_regions() {
    local models_var=$1
    local capacities_var=$2
    
    # Use indirect expansion instead of nameref for bash 3.2 compatibility
    eval "local models=(\"\${${models_var}[@]}\")"
    eval "local capacities=(\"\${${capacities_var}[@]}\")"
    
    local available_regions=()

    for region in "${CANDIDATE_REGIONS[@]}"; do
        local all_ok=true
        # Check each model in the group
        for i in "${!models[@]}"; do
            local model="${models[$i]}"
            local required="${capacities[$i]}"
            
            # Check model availability (model list + quota dimension exists)
            if ! is_model_available "$region" "$model"; then
                all_ok=false
                continue
            fi
            
            # If Azure exposes a quota dimension for this model, enforce it.
            # If not, rely on model-list availability; azd preflight also omits warnings for those models.
            local quota_info
            quota_info=$(get_quota_info "$region" "$model")
            if [ -n "$quota_info" ]; then
                if ! has_quota_for_model "$region" "$model" "$required"; then
                    all_ok=false
                fi
            fi
        done
        
        if [ "$all_ok" = true ]; then
            available_regions+=("$region")
        fi
    done
    
    # ONLY stdout: one qualifying region per line for the caller to collect.
    printf '%s\n' "${available_regions[@]+"${available_regions[@]}"}"
}

# ──────────────────────────────────────────────────────────────────
# Interactive region picker
# ALL UI output goes to stderr; stdout contains ONLY the selected region for command substitution
# ──────────────────────────────────────────────────────────────────
pick_region() {
    local group_name=$1
    local regions_var=$2
    local default_region=$3
    
    # Use indirect expansion instead of nameref for bash 3.2 compatibility
    eval "local regions=(\"\${${regions_var}[@]}\")"
    
    if [ ${#regions[@]} -eq 0 ]; then
        echo "" >&2
        echo "❌ No regions found with availability and quota for $group_name models" >&2
        echo "   Possible actions:" >&2
        echo "   1. Request quota increase in Azure Portal for OpenAI Standard deployments" >&2
        echo "   2. Manually set the env var and provision in a region you know has quota:" >&2
        echo "      azd env set AZURE_OPENAI_LOCATION_${group_name^^} <region>" >&2
        echo "" >&2
        exit 1
    fi
    
    echo "" >&2
    echo "Available regions for $group_name (with quota):" >&2
    echo "" >&2
    
    local default_idx=""
    for i in "${!regions[@]}"; do
        local marker=""
        if [ "${regions[$i]}" = "$default_region" ]; then
            marker=" (current default)"
            default_idx=$((i + 1))
        fi
        echo "  $((i + 1)). ${regions[$i]}$marker" >&2
    done
    
    echo "" >&2
    if [ -n "$default_idx" ]; then
        read -rp "Select region for $group_name [$default_idx]: " choice </dev/tty
        choice=${choice:-$default_idx}
    else
        read -rp "Select region for $group_name: " choice </dev/tty
    fi
    
    # Validate choice
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#regions[@]}" ]; then
        echo "❌ Invalid selection" >&2
        exit 1
    fi
    
    local selected="${regions[$((choice - 1))]}"
    echo "✅ Selected: $selected" >&2
    
    # ONLY stdout: the selected region for command substitution
    printf '%s\n' "$selected"
}

# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
main() {
    echo "=== Azure OpenAI Model Region Selection ===" >&2
    echo "" >&2
    
    # Check Azure CLI login
    check_az_login
    
    # Check if running in non-interactive mode
    if is_noninteractive; then
        # Non-interactive mode requires all env vars to be pre-set
        PRIMARY_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_PRIMARY)
        VOICE_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_VOICE)
        RESEARCH_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_RESEARCH)
        
        if [ -z "$PRIMARY_LOC" ] || [ -z "$VOICE_LOC" ] || [ -z "$RESEARCH_LOC" ]; then
            echo "❌ Error: running in non-interactive mode (CI) but required env vars not set" >&2
            echo "" >&2
            echo "   Set these environment variables before running azd up:" >&2
            echo "   - AZURE_OPENAI_LOCATION_PRIMARY" >&2
            echo "   - AZURE_OPENAI_LOCATION_VOICE" >&2
            echo "   - AZURE_OPENAI_LOCATION_RESEARCH" >&2
            echo "" >&2
            echo "   Example:" >&2
            echo "     azd env set AZURE_OPENAI_LOCATION_PRIMARY eastus2" >&2
            echo "     azd env set AZURE_OPENAI_LOCATION_VOICE centralus" >&2
            echo "     azd env set AZURE_OPENAI_LOCATION_RESEARCH westus" >&2
            echo "" >&2
            exit 1
        fi
        
        echo "Non-interactive mode: using pre-set regions" >&2
        echo "  Primary:  $PRIMARY_LOC" >&2
        echo "  Voice:    $VOICE_LOC" >&2
        echo "  Research: $RESEARCH_LOC" >&2
        echo "" >&2
        exit 0
    fi
    
    # Interactive mode — check if env vars are already set and validate them
    PRIMARY_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_PRIMARY)
    VOICE_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_VOICE)
    RESEARCH_LOC=$(get_azd_env AZURE_OPENAI_LOCATION_RESEARCH)
    
    # Validate existing env vars against quota
    # If any region no longer has quota for its models, clear it and re-prompt
    if [ -n "$PRIMARY_LOC" ]; then
        local primary_valid=true
        for i in "${!PRIMARY_MODELS[@]}"; do
            if ! has_quota_for_model "$PRIMARY_LOC" "${PRIMARY_MODELS[$i]}" "${PRIMARY_CAPACITY[$i]}"; then
                echo "⚠️  Warning: Previously selected PRIMARY region ($PRIMARY_LOC) no longer has quota for ${PRIMARY_MODELS[$i]}" >&2
                echo "   Clearing AZURE_OPENAI_LOCATION_PRIMARY — you will be re-prompted" >&2
                echo "" >&2
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
                echo "⚠️  Warning: Previously selected VOICE region ($VOICE_LOC) no longer has quota for ${VOICE_MODELS[$i]}" >&2
                echo "   Clearing AZURE_OPENAI_LOCATION_VOICE — you will be re-prompted" >&2
                echo "" >&2
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
                echo "⚠️  Warning: Previously selected RESEARCH region ($RESEARCH_LOC) no longer has quota for ${RESEARCH_MODELS[$i]}" >&2
                echo "   Clearing AZURE_OPENAI_LOCATION_RESEARCH — you will be re-prompted" >&2
                echo "" >&2
                RESEARCH_LOC=""
                research_valid=false
                break
            fi
        done
    fi
    
    # Skip prompt if all env vars are set and still valid
    if [ -n "$PRIMARY_LOC" ] && [ -n "$VOICE_LOC" ] && [ -n "$RESEARCH_LOC" ]; then
        echo "✅ Model regions already configured:" >&2
        echo "   Primary:  $PRIMARY_LOC" >&2
        echo "   Voice:    $VOICE_LOC" >&2
        echo "   Research: $RESEARCH_LOC" >&2
        echo "" >&2
        echo "To re-select regions, unset the env vars first:" >&2
        echo "  azd env set AZURE_OPENAI_LOCATION_PRIMARY ''" >&2
        echo "  azd env set AZURE_OPENAI_LOCATION_VOICE ''" >&2
        echo "  azd env set AZURE_OPENAI_LOCATION_RESEARCH ''" >&2
        echo "" >&2
        exit 0
    fi
    
    # ────────────────────────────────────────────────────────────
    # Primary Foundry (gpt-5.2, gpt-4.1, gpt-4o-transcribe)
    # ────────────────────────────────────────────────────────────
    if [ -z "$PRIMARY_LOC" ]; then
        echo "Finding Primary Foundry regions with available quota..." >&2
        primary_regions=()
        while IFS= read -r _region; do
            [ -n "$_region" ] && primary_regions+=("$_region")
        done < <(find_available_regions PRIMARY_MODELS PRIMARY_CAPACITY)
        PRIMARY_LOC=$(pick_region "PRIMARY" primary_regions "$DEFAULT_PRIMARY")
        if ! azd env set AZURE_OPENAI_LOCATION_PRIMARY "$PRIMARY_LOC"; then
            echo "❌ Failed to persist AZURE_OPENAI_LOCATION_PRIMARY" >&2
            exit 1
        fi
    else
        echo "✅ Primary region already set: $PRIMARY_LOC" >&2
    fi
    
    # ────────────────────────────────────────────────────────────
    # Voice Foundry (gpt-realtime)
    # ────────────────────────────────────────────────────────────
    if [ -z "$VOICE_LOC" ]; then
        echo "" >&2
        echo "Finding Voice Foundry regions with available quota..." >&2
        voice_regions=()
        while IFS= read -r _region; do
            [ -n "$_region" ] && voice_regions+=("$_region")
        done < <(find_available_regions VOICE_MODELS VOICE_CAPACITY)
        VOICE_LOC=$(pick_region "VOICE" voice_regions "$DEFAULT_VOICE")
        if ! azd env set AZURE_OPENAI_LOCATION_VOICE "$VOICE_LOC"; then
            echo "❌ Failed to persist AZURE_OPENAI_LOCATION_VOICE" >&2
            exit 1
        fi
    else
        echo "✅ Voice region already set: $VOICE_LOC" >&2
    fi
    
    # ────────────────────────────────────────────────────────────
    # Research Foundry (o3-deep-research)
    # ────────────────────────────────────────────────────────────
    if [ -z "$RESEARCH_LOC" ]; then
        echo "" >&2
        echo "Finding Research Foundry regions with available quota..." >&2
        research_regions=()
        while IFS= read -r _region; do
            [ -n "$_region" ] && research_regions+=("$_region")
        done < <(find_available_regions RESEARCH_MODELS RESEARCH_CAPACITY)
        RESEARCH_LOC=$(pick_region "RESEARCH" research_regions "$DEFAULT_RESEARCH")
        if ! azd env set AZURE_OPENAI_LOCATION_RESEARCH "$RESEARCH_LOC"; then
            echo "❌ Failed to persist AZURE_OPENAI_LOCATION_RESEARCH" >&2
            exit 1
        fi
    else
        echo "✅ Research region already set: $RESEARCH_LOC" >&2
    fi
    
    # ────────────────────────────────────────────────────────────
    # Summary & Verification
    # ────────────────────────────────────────────────────────────
    echo "" >&2
    echo "=== Region Selection Complete ===" >&2
    echo "  Primary:  $PRIMARY_LOC (gpt-5.2, gpt-4.1, gpt-4o-transcribe)" >&2
    echo "  Voice:    $VOICE_LOC (gpt-realtime)" >&2
    echo "  Research: $RESEARCH_LOC (o3-deep-research)" >&2
    echo "" >&2
    
    # Verify persistence by reading back the values
    VERIFY_PRIMARY=$(get_azd_env AZURE_OPENAI_LOCATION_PRIMARY)
    VERIFY_VOICE=$(get_azd_env AZURE_OPENAI_LOCATION_VOICE)
    VERIFY_RESEARCH=$(get_azd_env AZURE_OPENAI_LOCATION_RESEARCH)
    
    if [ "$VERIFY_PRIMARY" != "$PRIMARY_LOC" ] || [ "$VERIFY_VOICE" != "$VOICE_LOC" ] || [ "$VERIFY_RESEARCH" != "$RESEARCH_LOC" ]; then
        echo "❌ Persistence verification failed!" >&2
        echo "   Expected: PRIMARY=$PRIMARY_LOC VOICE=$VOICE_LOC RESEARCH=$RESEARCH_LOC" >&2
        echo "   Got:      PRIMARY=$VERIFY_PRIMARY VOICE=$VERIFY_VOICE RESEARCH=$VERIFY_RESEARCH" >&2
        exit 1
    fi
    
    echo "✅ Verified: all regions persisted successfully" >&2
    echo "Stored in azd environment. Proceeding with deployment..." >&2
    echo "" >&2
}

main "$@"
