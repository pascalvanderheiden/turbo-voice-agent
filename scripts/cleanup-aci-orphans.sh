#!/usr/bin/env bash
# cleanup-aci-orphans.sh
#
# One-shot, idempotent safety net for users upgrading from the legacy
# ACI-based sandbox to the Azure Container Apps dynamic session pool.
#
# Old architecture provisioned per-task `sandbox-*` Azure Container Instances
# (Microsoft.ContainerInstance/containerGroups) into the resource group.
# These are no longer created — but stale instances from previous deployments
# may linger and incur cost until deleted.
#
# Usage:
#   scripts/cleanup-aci-orphans.sh                 # interactive, reads RG from azd env
#   scripts/cleanup-aci-orphans.sh <resource-group>  # interactive, explicit RG
#   scripts/cleanup-aci-orphans.sh --yes           # non-interactive (CI)
#   scripts/cleanup-aci-orphans.sh <rg> --yes      # explicit RG + non-interactive
#
# Exits 0 cleanly when nothing to delete or after successful deletion.

set -euo pipefail

RG=""
ASSUME_YES=false

for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=true ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *) RG="$arg" ;;
  esac
done

# Resolve resource group from azd env if not provided
if [ -z "$RG" ]; then
  if command -v azd >/dev/null 2>&1; then
    RG=$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null || true)
  fi
fi

if [ -z "$RG" ]; then
  echo "❌  Resource group not specified and could not be read from azd env."
  echo "    Usage: $0 <resource-group> [--yes]"
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "❌  Azure CLI (az) not found on PATH."
  exit 1
fi

echo "🔍  Scanning resource group '$RG' for legacy ACI container groups..."

# List container groups; tolerate empty / missing RG
GROUPS_JSON=$(az container list -g "$RG" --query "[].{name:name, id:id, state:instanceView.state}" -o json 2>/dev/null || echo "[]")
COUNT=$(echo "$GROUPS_JSON" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
  echo "✅  No ACI container groups found in '$RG'. Nothing to clean up."
  exit 0
fi

echo ""
echo "Found $COUNT ACI container group(s):"
echo "$GROUPS_JSON" | python3 -c "
import sys, json
for g in json.load(sys.stdin):
    print(f\"  • {g['name']}  ({g.get('state', 'unknown')})\")
"
echo ""

if [ "$ASSUME_YES" != "true" ]; then
  read -r -p "Delete all of these? [y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) ;;
    *) echo "Aborted. No resources were deleted."; exit 0 ;;
  esac
fi

# Delete each one; --no-wait so a slow one doesn't block the rest
FAILED=0
echo "$GROUPS_JSON" | python3 -c "
import sys, json
for g in json.load(sys.stdin):
    print(g['name'])
" | while read -r name; do
  echo "🗑️   Deleting $name ..."
  if ! az container delete -g "$RG" -n "$name" --yes --no-wait >/dev/null 2>&1; then
    echo "    ⚠️  Failed to issue delete for $name"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "✅  Cleanup requested for $COUNT container group(s). Deletions run asynchronously."
echo "    Verify with: az container list -g '$RG' -o table"
exit 0
