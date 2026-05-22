#!/usr/bin/env bash
# Builds the sandbox container image directly in ACR using `az acr build`
# and tags it `turbo-voice-agent/sandbox:latest` — the exact reference the
# Azure Container Apps dynamic session pool (sp-sandbox-*) expects.
#
# Runs from:
#   - azd hooks: postprovision (after ACR exists) and postdeploy (refresh on code change)
#   - manually: bash infra/scripts/build-sandbox-image.sh
#
# Replaces the older `tag-sandbox-latest.sh` flow (which pushed a timestamped
# repo via `azd deploy sandbox` then re-tagged via `az acr import`). Since the
# sandbox is no longer an azd service, we build directly to the final tag.
#
# Idempotent: each invocation overwrites :latest with a fresh build.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SANDBOX_DIR="${REPO_ROOT}/sandbox"
TARGET_IMAGE="turbo-voice-agent/sandbox:latest"

# Resolve ACR login server from azd env (set by Bicep output AZURE_CONTAINER_REGISTRY)
ACR_LOGIN_SERVER=$(azd env get-value AZURE_CONTAINER_REGISTRY 2>/dev/null || true)
if [ -z "$ACR_LOGIN_SERVER" ]; then
  echo "⚠️  AZURE_CONTAINER_REGISTRY not set in azd env — skipping sandbox image build."
  echo "    (This is expected on first run before initial provision completes.)"
  exit 0
fi

# Extract ACR short name (e.g. "acr2mta7feoalzyq" from "acr2mta7feoalzyq.azurecr.io")
ACR_NAME="${ACR_LOGIN_SERVER%%.*}"

if [ ! -d "$SANDBOX_DIR" ]; then
  echo "❌  Sandbox directory not found: $SANDBOX_DIR"
  exit 1
fi

if [ ! -f "$SANDBOX_DIR/Dockerfile" ]; then
  echo "❌  Sandbox Dockerfile not found: $SANDBOX_DIR/Dockerfile"
  exit 1
fi

echo "🔨  Building sandbox image in ACR:"
echo "    Registry: $ACR_NAME"
echo "    Context:  $SANDBOX_DIR"
echo "    Image:    $TARGET_IMAGE"

az acr build \
  --registry "$ACR_NAME" \
  --image "$TARGET_IMAGE" \
  --file "$SANDBOX_DIR/Dockerfile" \
  "$SANDBOX_DIR"

echo "✅  Sandbox image published as ${ACR_LOGIN_SERVER}/${TARGET_IMAGE}"
echo "    The session pool (sp-sandbox-*) will pull this image on next session allocation."
