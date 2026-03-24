#!/bin/bash
# Initialize git repo in workspace if needed (Copilot CLI requires it)
if [ ! -d /workspace/.git ]; then
  cd /workspace && git init -q && git config user.email "agent@sandbox" && git config user.name "Sandbox Agent"
fi

# OpenSpec init moved to explicit pipeline stage (runs at dev_agent.py openspec stage)

# Sync custom skills from Azure Blob Storage (if running in Azure)
if [ -n "$AZURE_STORAGE_ACCOUNT_NAME" ]; then
  echo "Syncing skills from Blob Storage (account: $AZURE_STORAGE_ACCOUNT_NAME)..."
  /app/sync-skills.sh
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
