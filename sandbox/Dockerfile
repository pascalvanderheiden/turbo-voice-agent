FROM node:22-bookworm

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
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

# GitHub Copilot CLI extension
RUN gh extension install github/gh-copilot

# Playwright
RUN npm install -g playwright \
    && npx playwright install --with-deps chromium

# OpenSpec CLI
RUN npm install -g openspec

# Workspace for sandbox project work
RUN mkdir -p /workspace

# Server app
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY server.js ./

EXPOSE 3000

CMD ["node", "server.js"]
