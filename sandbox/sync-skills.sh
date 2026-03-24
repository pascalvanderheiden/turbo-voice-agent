#!/bin/bash
# sync-skills.sh — Download all skills from Azure Blob Storage
# Used by: entrypoint.sh (startup) and server.js (hot-reload endpoint)
#
# Returns the number of skills synced on stdout (last line).

SKILLS_DIR="/home/agent/.copilot/skills"
SYNCED=0

if [ -z "$AZURE_STORAGE_ACCOUNT_NAME" ]; then
  echo "No storage account configured — skipping skill sync."
  echo "0"
  exit 0
fi

if ! command -v az &>/dev/null; then
  echo "WARNING: az CLI not available — skipping skill sync."
  echo "0"
  exit 0
fi

# Ensure az is logged in with managed identity (idempotent)
# Use user-assigned identity client ID if provided (ACI mode), else system-assigned
if [ -n "$ACI_IDENTITY_CLIENT_ID" ]; then
  az login --identity --username "$ACI_IDENTITY_CLIENT_ID" --allow-no-subscriptions 2>/dev/null || true
else
  az login --identity --allow-no-subscriptions 2>/dev/null || true
fi

BLOBS=$(az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT_NAME" \
  --container-name skills \
  --auth-mode login \
  --query "[].name" -o tsv 2>/dev/null)

if [ -z "$BLOBS" ]; then
  echo "No skills found in Blob Storage."
  echo "0"
  exit 0
fi

# Track unique skill names (first path segment)
declare -A SKILL_NAMES

while IFS= read -r blob; do
  [ -z "$blob" ] && continue
  dest="$SKILLS_DIR/$blob"
  mkdir -p "$(dirname "$dest")"
  az storage blob download \
    --account-name "$AZURE_STORAGE_ACCOUNT_NAME" \
    --container-name skills \
    --name "$blob" \
    --file "$dest" \
    --auth-mode login \
    --no-progress 2>/dev/null && echo "  ✓ $blob"

  # Extract skill name (first path segment)
  skill_name="${blob%%/*}"
  SKILL_NAMES["$skill_name"]=1
done <<< "$BLOBS"

SYNCED=${#SKILL_NAMES[@]}
echo "Skills sync complete ($SYNCED skill(s))."
echo "$SYNCED"
