#!/usr/bin/env bash
# Post-deploy hook: tag the sandbox image as "turbo-voice-agent/sandbox:latest"
# so ACI container groups can pull a stable reference.
#
# azd pushes images with timestamped tags like:
#   turbo-voice-agent/sandbox-{envName}:azd-deploy-{ts}
# ACI needs a predictable name: turbo-voice-agent/sandbox:latest

set -euo pipefail

# Resolve ACR login server from azd env (set by Bicep output AZURE_CONTAINER_REGISTRY)
ACR_LOGIN_SERVER=$(azd env get-value AZURE_CONTAINER_REGISTRY 2>/dev/null || true)
if [ -z "$ACR_LOGIN_SERVER" ]; then
  echo "⚠️  AZURE_CONTAINER_REGISTRY not set — skipping sandbox image tagging."
  exit 0
fi

# Extract ACR short name (e.g. "acr2mta7feoalzyq" from "acr2mta7feoalzyq.azurecr.io")
ACR_NAME="${ACR_LOGIN_SERVER%%.*}"

# Find the sandbox repo in ACR (pattern: turbo-voice-agent/sandbox-*)
SANDBOX_REPO=$(az acr repository list --name "$ACR_NAME" -o tsv 2>/dev/null | grep "sandbox" | head -1)
if [ -z "$SANDBOX_REPO" ]; then
  echo "⚠️  No sandbox repository found in $ACR_NAME — skipping."
  exit 0
fi

# Get the latest tag
LATEST_TAG=$(az acr repository show-tags --name "$ACR_NAME" --repository "$SANDBOX_REPO" --orderby time_desc --top 1 -o tsv 2>/dev/null)
if [ -z "$LATEST_TAG" ]; then
  echo "⚠️  No tags found for $SANDBOX_REPO — skipping."
  exit 0
fi

SOURCE="${ACR_NAME}.azurecr.io/${SANDBOX_REPO}:${LATEST_TAG}"
TARGET="turbo-voice-agent/sandbox:latest"

echo "🏷️  Tagging sandbox image for ACI:"
echo "   Source: $SOURCE"
echo "   Target: ${ACR_NAME}.azurecr.io/${TARGET}"

az acr import \
  --name "$ACR_NAME" \
  --source "$SOURCE" \
  --image "$TARGET" \
  --force \
  --no-wait

echo "✅  Sandbox image tagged as $TARGET"
