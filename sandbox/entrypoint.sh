#!/bin/bash
# Copy OpenSpec skills into workspace (volume mounts override build-time COPY)
mkdir -p /workspace/.github/skills
cp -r /opt/openspec-skills/* /workspace/.github/skills/ 2>/dev/null || true

# Initialize git repo in workspace if needed (Copilot CLI may require it)
if [ ! -d /workspace/.git ]; then
  cd /workspace && git init -q && git config user.email "agent@sandbox" && git config user.name "Sandbox Agent"
fi

exec node /app/server.js
