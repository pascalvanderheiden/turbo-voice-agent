#!/usr/bin/env bash
# Collect all deployment parameters for azd up.
# Runs FIRST in preprovision phase — fetches from azd env, auto-discovers from Azure CLI,
# prompts only if interactive TTY and value is missing.
# Idempotent — safe to run multiple times.
set -euo pipefail

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
# Helpers
# ──────────────────────────────────────────────────────────────────
is_noninteractive() {
    [ "${GITHUB_ACTIONS:-}" = "true" ] || [ ! -t 0 ]
}

check_az_login() {
    if ! az account show &>/dev/null; then
        echo "❌ Error: not logged in to Azure CLI"
        echo "   Run: az login"
        exit 1
    fi
}

# ──────────────────────────────────────────────────────────────────
# Param: AZURE_SUBSCRIPTION_ID
# Auto-discover or prompt if multiple subscriptions available
# ──────────────────────────────────────────────────────────────────
collect_subscription() {
    local sub_id
    sub_id=$(get_azd_env AZURE_SUBSCRIPTION_ID)
    
    if [ -n "$sub_id" ]; then
        echo "✅ Subscription: $sub_id (from azd env)"
        az account set --subscription "$sub_id" 2>/dev/null || true
        return 0
    fi
    
    # Auto-discover current subscription
    sub_id=$(az account show --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$sub_id" ]; then
        azd env set AZURE_SUBSCRIPTION_ID "$sub_id"
        echo "✅ Subscription: $sub_id (auto-discovered)"
        return 0
    fi
    
    # Multiple subscriptions — need to pick
    local sub_count
    sub_count=$(az account list --query "length([])" -o tsv 2>/dev/null || echo "0")
    
    if [ "$sub_count" -eq 0 ]; then
        echo "❌ Error: no Azure subscriptions found"
        exit 1
    fi
    
    if is_noninteractive; then
        echo "❌ Error: multiple subscriptions available but running in non-interactive mode"
        echo "   Set AZURE_SUBSCRIPTION_ID before running azd up"
        exit 1
    fi
    
    # Interactive — list subscriptions and prompt
    echo ""
    echo "Available Azure subscriptions:"
    echo ""
    
    # List subscriptions with index
    local subs
    subs=$(az account list --query "[].{name:name, id:id}" -o tsv)
    local idx=1
    while IFS=$'\t' read -r name id; do
        echo "  $idx. $name ($id)"
        ((idx++))
    done <<< "$subs"
    
    echo ""
    read -rp "Select subscription [1]: " choice
    choice=${choice:-1}
    
    # Validate choice
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "$sub_count" ]; then
        echo "❌ Invalid selection"
        exit 1
    fi
    
    # Extract selected subscription ID
    sub_id=$(echo "$subs" | sed -n "${choice}p" | awk '{print $NF}')
    
    azd env set AZURE_SUBSCRIPTION_ID "$sub_id"
    az account set --subscription "$sub_id"
    echo "✅ Subscription: $sub_id"
}

# ──────────────────────────────────────────────────────────────────
# Param: AZURE_LOCATION
# Used by azd for resource group location. azd init/up usually sets this.
# Only prompt if truly empty.
# ──────────────────────────────────────────────────────────────────
collect_location() {
    local location
    location=$(get_azd_env AZURE_LOCATION)
    
    if [ -n "$location" ]; then
        echo "✅ Location: $location (from azd env)"
        return 0
    fi
    
    # azd normally sets this during env new, so if it's missing in interactive mode, prompt
    if is_noninteractive; then
        # CI mode — azd should have set it, but allow fallback to eastus2
        azd env set AZURE_LOCATION "eastus2"
        echo "✅ Location: eastus2 (fallback)"
        return 0
    fi
    
    # Interactive — prompt with common regions
    echo ""
    echo "Select Azure region for resource group:"
    echo "  1. eastus2 (default)"
    echo "  2. westus2"
    echo "  3. centralus"
    echo "  4. westeurope"
    echo "  5. uksouth"
    echo ""
    read -rp "Select region [1]: " choice
    choice=${choice:-1}
    
    case "$choice" in
        1) location="eastus2" ;;
        2) location="westus2" ;;
        3) location="centralus" ;;
        4) location="westeurope" ;;
        5) location="uksouth" ;;
        *) location="eastus2" ;;
    esac
    
    azd env set AZURE_LOCATION "$location"
    echo "✅ Location: $location"
}

# ──────────────────────────────────────────────────────────────────
# Param: ENTRA_TENANT_ID
# Auto-discover from az account show. Never prompt.
# ──────────────────────────────────────────────────────────────────
collect_tenant() {
    local tenant_id
    tenant_id=$(get_azd_env ENTRA_TENANT_ID)
    
    if [ -n "$tenant_id" ]; then
        echo "✅ Tenant ID: $tenant_id (from azd env)"
        return 0
    fi
    
    # Auto-discover
    tenant_id=$(az account show --query tenantId -o tsv 2>/dev/null || echo "")
    if [ -z "$tenant_id" ]; then
        echo "❌ Error: could not auto-discover tenant ID"
        exit 1
    fi
    
    azd env set ENTRA_TENANT_ID "$tenant_id"
    echo "✅ Tenant ID: $tenant_id (auto-discovered)"
}

# ──────────────────────────────────────────────────────────────────
# Param: CUSTOM_DOMAIN_NAME
# Optional — prompt once in interactive mode, accept empty
# ──────────────────────────────────────────────────────────────────
collect_custom_domain() {
    local domain
    domain=$(get_azd_env CUSTOM_DOMAIN_NAME)
    
    if [ -n "$(get_azd_env CUSTOM_DOMAIN_CONFIGURED)" ]; then
        if [ -n "$domain" ]; then
            echo "✅ Custom domain: $domain (from azd env)"
        else
            echo "✅ Custom domain: none (using Container Apps default)"
        fi
        return 0
    fi
    
    if is_noninteractive; then
        azd env set CUSTOM_DOMAIN_NAME ""
        azd env set CUSTOM_DOMAIN_CONFIGURED "true"
        echo "✅ Custom domain: none (using Container Apps default)"
        return 0
    fi
    
    echo ""
    read -rp "Custom domain name (leave empty to use Container Apps default): " domain </dev/tty
    azd env set CUSTOM_DOMAIN_NAME "$domain"
    azd env set CUSTOM_DOMAIN_CONFIGURED "true"
    
    if [ -n "$domain" ]; then
        echo "✅ Custom domain: $domain"
    else
        echo "✅ Custom domain: none (using Container Apps default)"
    fi
}

# ──────────────────────────────────────────────────────────────────
# Param: EXISTING_CERT_NAME
# Optional — only prompt if CUSTOM_DOMAIN_NAME is non-empty
# ──────────────────────────────────────────────────────────────────
collect_cert_name() {
    local cert
    cert=$(get_azd_env EXISTING_CERT_NAME)
    
    if [ -n "$(get_azd_env EXISTING_CERT_CONFIGURED)" ]; then
        if [ -n "$cert" ]; then
            echo "✅ Managed certificate: $cert (from azd env)"
        fi
        return 0
    fi
    
    # Only prompt if custom domain is set
    local domain
    domain=$(get_azd_env CUSTOM_DOMAIN_NAME)
    
    if [ -z "$domain" ]; then
        azd env set EXISTING_CERT_NAME ""
        azd env set EXISTING_CERT_CONFIGURED "true"
        return 0
    fi
    
    if is_noninteractive; then
        azd env set EXISTING_CERT_NAME ""
        azd env set EXISTING_CERT_CONFIGURED "true"
        return 0
    fi
    
    echo ""
    read -rp "Existing managed certificate name (leave empty to skip): " cert </dev/tty
    azd env set EXISTING_CERT_NAME "$cert"
    azd env set EXISTING_CERT_CONFIGURED "true"
    
    if [ -n "$cert" ]; then
        echo "✅ Managed certificate: $cert"
    fi
}

# ──────────────────────────────────────────────────────────────────
# Param: ENTRA_CLIENT_SECRET
# Optional — only needed for Microsoft To Do OAuth. Prompt once.
# ──────────────────────────────────────────────────────────────────
collect_client_secret() {
    local secret
    
    # If already set (even to empty), skip
    if [ -n "$(get_azd_env ENTRA_CLIENT_SECRET)" ]; then
        echo "✅ Entra client secret: (from azd env)"
        return 0
    fi
    
    if is_noninteractive; then
        azd env set ENTRA_CLIENT_SECRET ""
        return 0
    fi
    
    # Interactive — prompt with explanation
    echo ""
    echo "Entra client secret (optional — only needed for Microsoft To Do OAuth)"
    read -rsp "Press Enter to skip, or paste secret: " secret
    echo ""
    
    # Try to use --secret flag if azd supports it, else fallback to regular set
    if azd env set --help 2>&1 | grep -q -- '--secret'; then
        azd env set --secret ENTRA_CLIENT_SECRET "$secret" 2>/dev/null || azd env set ENTRA_CLIENT_SECRET "$secret"
    else
        azd env set ENTRA_CLIENT_SECRET "$secret"
    fi
    
    if [ -n "$secret" ]; then
        echo "✅ Entra client secret: set"
    else
        echo "✅ Entra client secret: none (skipped)"
    fi
}

# ──────────────────────────────────────────────────────────────────
# Param: DEPLOYER_PRINCIPAL_ID
# Auto-discover from az ad signed-in-user show. Never prompt.
# ──────────────────────────────────────────────────────────────────
collect_deployer_principal() {
    local principal_id
    principal_id=$(get_azd_env DEPLOYER_PRINCIPAL_ID)
    
    if [ -n "$principal_id" ]; then
        echo "✅ Deployer principal ID: $principal_id (from azd env)"
        return 0
    fi
    
    # Auto-discover signed-in user object ID
    principal_id=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
    
    # If running as service principal (CI), this will fail — that's OK, leave empty
    if [ -z "$principal_id" ]; then
        azd env set DEPLOYER_PRINCIPAL_ID ""
        echo "✅ Deployer principal ID: none (service principal or unavailable)"
        return 0
    fi
    
    azd env set DEPLOYER_PRINCIPAL_ID "$principal_id"
    echo "✅ Deployer principal ID: $principal_id (auto-discovered)"
}

# ──────────────────────────────────────────────────────────────────
# Param: DEPLOY_RBAC
# Default to "true". Never prompt.
# ──────────────────────────────────────────────────────────────────
collect_deploy_rbac() {
    local deploy_rbac
    deploy_rbac=$(get_azd_env DEPLOY_RBAC)
    
    if [ -n "$deploy_rbac" ]; then
        echo "✅ Deploy RBAC: $deploy_rbac (from azd env)"
        return 0
    fi
    
    azd env set DEPLOY_RBAC "true"
    echo "✅ Deploy RBAC: true (default)"
}

# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
main() {
    echo "=== Deployment Parameter Collection ==="
    echo ""
    
    # Check Azure CLI login first
    check_az_login
    
    # Collect params in order
    collect_subscription
    collect_location
    collect_tenant
    collect_custom_domain
    collect_cert_name
    collect_client_secret
    collect_deployer_principal
    collect_deploy_rbac
    
    # Summary
    echo ""
    echo "=== Resolved Deployment Parameters ==="
    echo "  Subscription:    $(v=$(get_azd_env AZURE_SUBSCRIPTION_ID); echo "${v:-N/A}")"
    echo "  Location:        $(v=$(get_azd_env AZURE_LOCATION); echo "${v:-N/A}")"
    echo "  Tenant ID:       $(v=$(get_azd_env ENTRA_TENANT_ID); echo "${v:-N/A}")"
    echo "  Custom domain:   $(v=$(get_azd_env CUSTOM_DOMAIN_NAME); echo "${v:-none}")"
    echo "  Certificate:     $(v=$(get_azd_env EXISTING_CERT_NAME); echo "${v:-none}")"
    echo "  Client secret:   $([ -n "$(v=$(get_azd_env ENTRA_CLIENT_SECRET); echo "${v:-}")" ] && echo '***' || echo 'none')"
    echo "  Deployer ID:     $(v=$(get_azd_env DEPLOYER_PRINCIPAL_ID); echo "${v:-none}")"
    echo "  Deploy RBAC:     $(v=$(get_azd_env DEPLOY_RBAC); echo "${v:-true}")"
    echo ""
}

main "$@"
