FROM node:22-bookworm

# System dependencies (mirrors official docker/sandbox-templates:copilot)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    sudo \
    python3 \
    python3-pip \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# GitHub Copilot CLI (installed globally via npm, same as official sandbox)
RUN npm install -g @github/copilot

# Playwright (for screenshot generation)
RUN npm install -g playwright \
    && npx playwright install --with-deps chromium

# OpenSpec CLI
RUN npm install -g openspec

# Create non-root agent user (mirrors official sandbox template pattern)
RUN useradd -m -s /bin/bash agent \
    && echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Workspace for sandbox project work
RUN mkdir -p /workspace && chown agent:agent /workspace

# Configure Copilot CLI: trust /workspace, enable yolo mode
RUN mkdir -p /home/agent/.copilot \
    && echo '{ "trustedFolders": ["/workspace"], "yolo": true }' \
       > /home/agent/.copilot/config.json \
    && chown -R agent:agent /home/agent/.copilot

# Server app
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY server.js ./
RUN chown -R agent:agent /app

USER agent

EXPOSE 3000

CMD ["node", "server.js"]
