#!/bin/bash
# upload-skills.sh — Seed the `skills` blob container with the platform skills
# bundled at .github/skills/.
#
# Background: the sandbox image's entrypoint (sandbox/sync-skills.sh) pulls
# every blob from the `skills` container into /home/agent/.copilot/skills/ at
# session warm-up. The blob container itself is provisioned empty by
# infra/modules/storage.bicep — so unless something seeds it, every freshly
# deployed environment has zero skills available in its sandboxes.
#
# Per-user marketplace activations (CosmosSkillsService.upload_skill_from_github_to_blob)
# also write into this container, but the .github/skills/ set is the baseline
# every deployment should ship with. This script is idempotent and safe to
# re-run from `azd up` postprovision.
#
# Auth: --auth-mode login (uses the deployer's credential — same one azd uses).
# Requires the deployer to have "Storage Blob Data Contributor" on the account.

set -euo pipefail

SKILLS_SRC="$(cd "$(dirname "$0")/../.." && pwd)/.github/skills"
CONTAINER="skills"

# Discover the storage account.
# Preferred source: azd env var (added as a Bicep output in this change).
# Fallback: query by resource group.
ACCOUNT="${AZURE_STORAGE_ACCOUNT_NAME:-}"

if [ -z "$ACCOUNT" ] && [ -n "${AZURE_RESOURCE_GROUP:-}" ]; then
  ACCOUNT="$(az storage account list \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query "[0].name" -o tsv 2>/dev/null || true)"
fi

if [ -z "$ACCOUNT" ]; then
  echo "upload-skills: no storage account found (AZURE_STORAGE_ACCOUNT_NAME and AZURE_RESOURCE_GROUP both unset) — skipping."
  exit 0
fi

if [ ! -d "$SKILLS_SRC" ]; then
  echo "upload-skills: source directory $SKILLS_SRC not found — skipping."
  exit 0
fi

echo "upload-skills: uploading $SKILLS_SRC → $ACCOUNT/$CONTAINER"

# The storage account uses networkAcls.defaultAction='Deny' (see
# infra/modules/storage.bicep), so the deployer's public IP must be on the
# allowlist for blob data-plane calls. We open it just for this upload and
# remove it afterwards. The az CLI accepts a single IP (not CIDR) for
# /32 entries.
CALLER_IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
IP_ADDED=0

cleanup_ip() {
  if [ "$IP_ADDED" = "1" ] && [ -n "$CALLER_IP" ]; then
    echo "upload-skills: removing temporary firewall rule for $CALLER_IP"
    az storage account network-rule remove \
      --account-name "$ACCOUNT" \
      --resource-group "${AZURE_RESOURCE_GROUP:-}" \
      --ip-address "$CALLER_IP" \
      --output none 2>/dev/null || true
  fi
}
trap cleanup_ip EXIT

do_upload() {
  az storage blob upload-batch \
    --account-name "$ACCOUNT" \
    --destination "$CONTAINER" \
    --source "$SKILLS_SRC" \
    --auth-mode login \
    --overwrite \
    --output none 2>&1
}

if ! UPLOAD_ERR="$(do_upload)"; then
  # Network rule failure? Try opening the firewall for this run only.
  if echo "$UPLOAD_ERR" | grep -qi "network rules\|AuthorizationFailure\|not allowed"; then
    if [ -n "$CALLER_IP" ] && [ -n "${AZURE_RESOURCE_GROUP:-}" ]; then
      echo "upload-skills: storage firewall blocked the call; adding $CALLER_IP temporarily"
      if az storage account network-rule add \
           --account-name "$ACCOUNT" \
           --resource-group "$AZURE_RESOURCE_GROUP" \
           --ip-address "$CALLER_IP" \
           --output none 2>/dev/null; then
        IP_ADDED=1
        # ACL propagation lag — Azure Storage network rule changes can take
        # 30-60s to take effect on the data plane. Verified empirically.
        sleep 60
        if ! UPLOAD_ERR="$(do_upload)"; then
          echo "upload-skills: WARNING — retry after firewall open still failed:"
          echo "$UPLOAD_ERR"
          exit 0
        fi
      else
        echo "upload-skills: WARNING — could not add firewall rule (need 'Storage Account Contributor'). Original error:"
        echo "$UPLOAD_ERR"
        exit 0
      fi
    else
      echo "upload-skills: WARNING — firewall block but caller IP / resource group unknown:"
      echo "$UPLOAD_ERR"
      exit 0
    fi
  else
    echo "upload-skills: WARNING — upload failed:"
    echo "$UPLOAD_ERR"
    echo "Sandbox will start with zero platform skills; users can still activate skills via the marketplace."
    exit 0
  fi
fi

COUNT=$(find "$SKILLS_SRC" -type f | wc -l | tr -d ' ')
echo "upload-skills: ✓ uploaded $COUNT file(s) across $(ls -1 "$SKILLS_SRC" | wc -l | tr -d ' ') skill(s)."
