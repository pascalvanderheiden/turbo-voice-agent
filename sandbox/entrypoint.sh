#!/bin/bash
# Initialize git repo in workspace if needed (Copilot CLI requires it)
if [ ! -d /workspace/.git ]; then
  cd /workspace && git init -q && git config user.email "agent@sandbox" && git config user.name "Sandbox Agent"
fi

# Initialize OpenSpec with GitHub Copilot skills (generates .github/skills/)
cd /workspace && openspec init --tools github-copilot --force 2>/dev/null || true

# Sync custom skills from Azure Blob Storage (if running in Azure)
if [ -n "$AZURE_STORAGE_ACCOUNT_NAME" ]; then
  echo "Syncing skills from Blob Storage (account: $AZURE_STORAGE_ACCOUNT_NAME)..."
  SKILLS_DIR="/home/agent/.copilot/skills"
  # Use az CLI with managed identity to list and download skill blobs
  if command -v az &>/dev/null; then
    az login --identity --allow-no-subscriptions 2>/dev/null || true
    # List all blobs in the skills container and download them
    BLOBS=$(az storage blob list \
      --account-name "$AZURE_STORAGE_ACCOUNT_NAME" \
      --container-name skills \
      --auth-mode login \
      --query "[].name" -o tsv 2>/dev/null)
    if [ -n "$BLOBS" ]; then
      while IFS= read -r blob; do
        dest="$SKILLS_DIR/$blob"
        mkdir -p "$(dirname "$dest")"
        az storage blob download \
          --account-name "$AZURE_STORAGE_ACCOUNT_NAME" \
          --container-name skills \
          --name "$blob" \
          --file "$dest" \
          --auth-mode login \
          --no-progress 2>/dev/null && echo "  ✓ $blob"
      done <<< "$BLOBS"
      echo "Skills sync complete."
    else
      echo "No custom skills found in Blob Storage."
    fi
  else
    echo "WARNING: az CLI not available — skipping skill sync from Blob Storage."
  fi
fi

# List installed skills on startup (CLI-based verification happens at pipeline time)
echo "=== Installed Skills ==="
echo ""
echo "Workspace skills (.github/skills/):"
if [ -d /workspace/.github/skills ] && [ "$(ls -A /workspace/.github/skills 2>/dev/null)" ]; then
  ls -1 /workspace/.github/skills/ 2>/dev/null | while read name; do
    echo "  • $name"
  done
else
  echo "  (none — installed at pipeline time)"
fi
echo ""
echo "User skills (~/.copilot/skills/):"
if [ -d /home/agent/.copilot/skills ] && [ "$(ls -A /home/agent/.copilot/skills 2>/dev/null)" ]; then
  ls -1 /home/agent/.copilot/skills/ 2>/dev/null | while read name; do
    echo "  • $name"
  done
else
  echo "  (none)"
fi
echo ""
echo "Note: Copilot CLI skill verification runs at pipeline init time."
echo "==========================="

exec node /app/server.js
