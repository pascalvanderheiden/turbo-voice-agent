#!/usr/bin/env bash
# Setup Entra ID app registration for Turbo Voice Agent.
# Idempotent — safe to run multiple times. Skips creation if app already exists.
# Skips entirely in CI — Entra app is managed locally, CI sets vars via azd env set.
set -euo pipefail

if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    echo "Running in GitHub Actions — skipping Entra ID setup (vars set externally)"
    exit 0
fi

APP_NAME="Turbo Voice Agent"
CUSTOM_DOMAIN="${CUSTOM_DOMAIN_NAME:-}"

echo "=== Entra ID App Registration Setup ==="

# Get tenant ID from current Azure CLI session
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "Tenant ID: $TENANT_ID"

# Check if app already exists
EXISTING_APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [ -n "$EXISTING_APP_ID" ] && [ "$EXISTING_APP_ID" != "None" ]; then
    echo "App registration already exists: $EXISTING_APP_ID"
    CLIENT_ID="$EXISTING_APP_ID"
else
    echo "Creating app registration: $APP_NAME"
    CLIENT_ID=$(az ad app create \
        --display-name "$APP_NAME" \
        --sign-in-audience "AzureADMyOrg" \
        --query appId -o tsv)
    echo "Created app registration: $CLIENT_ID"

    # Create service principal
    az ad sp create --id "$CLIENT_ID" --query id -o tsv >/dev/null 2>&1 || true
    echo "Service principal created"
fi

# Configure SPA redirect URIs
echo "Configuring SPA redirect URIs..."
URIS="http://localhost:3000"
if [ -n "$CUSTOM_DOMAIN" ]; then
  URIS="$URIS https://${CUSTOM_DOMAIN}"
fi
if [ -n "${FRONTEND_URL:-}" ]; then
  URIS="$URIS ${FRONTEND_URL}"
fi
az ad app update --id "$CLIENT_ID" \
    --set "spa={\"redirectUris\":[$(echo $URIS | sed 's/ /","/g' | sed 's/^/"/' | sed 's/$/"/' )]}" \
    2>/dev/null || true

# Set Application ID URI and expose API scope
APP_ID_URI="api://$CLIENT_ID"
echo "Setting Application ID URI: $APP_ID_URI"
az ad app update --id "$CLIENT_ID" \
    --identifier-uris "$APP_ID_URI" \
    2>/dev/null || true

# Add the 'access' scope if it doesn't exist
EXISTING_SCOPES=$(az ad app show --id "$CLIENT_ID" --query "api.oauth2PermissionScopes[?value=='access'].id" -o tsv 2>/dev/null || true)
if [ -z "$EXISTING_SCOPES" ]; then
    echo "Adding 'access' API scope..."
    SCOPE_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]')
    az ad app update --id "$CLIENT_ID" \
        --set "api={\"oauth2PermissionScopes\":[{\"adminConsentDescription\":\"Access Turbo Voice Agent\",\"adminConsentDisplayName\":\"Access Turbo Voice Agent\",\"id\":\"$SCOPE_ID\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Access Turbo Voice Agent\",\"userConsentDisplayName\":\"Access Turbo Voice Agent\",\"value\":\"access\"}]}" \
        2>/dev/null || true
    echo "API scope 'access' created"
else
    echo "API scope 'access' already exists"
fi

# Determine redirect URI for production
if [ -n "$CUSTOM_DOMAIN" ]; then
    REDIRECT_URI="https://$CUSTOM_DOMAIN"
elif [ -n "${FRONTEND_URL:-}" ]; then
    REDIRECT_URI="$FRONTEND_URL"
else
    REDIRECT_URI="http://localhost:3000"
fi

# Store values in azd environment for Bicep and Docker build args
echo "Storing values in azd environment..."
azd env set ENTRA_TENANT_ID "$TENANT_ID"
azd env set ENTRA_CLIENT_ID "$CLIENT_ID"
azd env set FRONTEND_REDIRECT_URI "$REDIRECT_URI"
if [ -n "$CUSTOM_DOMAIN" ]; then
    azd env set CUSTOM_DOMAIN_NAME "$CUSTOM_DOMAIN"
fi

echo "Entra ID app configuration persisted to azd environment"

echo ""
echo "=== Entra ID Setup Complete ==="
echo "  Tenant ID:    $TENANT_ID"
echo "  Client ID:    $CLIENT_ID"
echo "  Redirect URI: $REDIRECT_URI"
echo "  App ID URI:   $APP_ID_URI"
echo ""
