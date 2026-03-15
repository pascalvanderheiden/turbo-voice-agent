#!/bin/bash
# Initialize git repo in workspace if needed (Copilot CLI requires it)
if [ ! -d /workspace/.git ]; then
  cd /workspace && git init -q && git config user.email "agent@sandbox" && git config user.name "Sandbox Agent"
fi

# Initialize OpenSpec with GitHub Copilot skills (generates .github/skills/)
cd /workspace && openspec init --tools github-copilot --force 2>/dev/null || true

exec node /app/server.js
