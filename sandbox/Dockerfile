FROM node:22-bookworm

# System dependencies (mirrors official docker/sandbox-templates:copilot)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    sudo \
    python3 \
    python3-pip \
    chromium \
    ca-certificates \
    apt-transport-https \
    lsb-release \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Azure CLI (for downloading skills from Blob Storage in Azure)
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# GitHub Copilot CLI (installed globally via npm, same as official sandbox)
RUN npm install -g @github/copilot

# OpenSpec CLI (generates skills for Copilot CLI via `openspec init --tools github-copilot`)
RUN npm install -g @fission-ai/openspec@latest

# Squad CLI (multi-agent runtime for GitHub Copilot)
RUN npm install -g @bradygaster/squad-cli

# Playwright npm package (browser install deferred to after user creation)
RUN npm install -g playwright

# Create non-root agent user (mirrors official sandbox template pattern)
RUN useradd -m -s /bin/bash agent \
    && echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Workspace for sandbox project work
RUN mkdir -p /workspace && chown agent:agent /workspace

# Install Playwright browsers as agent user (must match runtime user)
USER agent
RUN npx playwright install --with-deps chromium
USER root

# Configure Copilot CLI: trust /workspace, enable yolo mode
RUN mkdir -p /home/agent/.copilot/skills \
    && echo '{ "trustedFolders": ["/workspace"], "yolo": true }' \
       > /home/agent/.copilot/config.json \
    && chown -R agent:agent /home/agent/.copilot

# Server app
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY server.js entrypoint.sh ./
RUN chmod +x entrypoint.sh && chown -R agent:agent /app

USER agent

EXPOSE 3000

CMD ["./entrypoint.sh"]
