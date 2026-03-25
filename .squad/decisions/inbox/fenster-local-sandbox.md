# Decision: Local Docker Sandbox Auto-Start

**Author:** Fenster  
**Date:** 2025-07-25  
**Status:** Implemented

## Context

The dev pipeline requires a running sandbox container (Copilot CLI + Node.js server on port 3000). In production, ACI provisions per-task containers. In local dev, the sandbox is defined in `docker-compose.yml` but developers had to manually run `docker compose up -d sandbox` before starting the backend — easy to forget, leading to confusing "sandbox not reachable" errors.

## Decision

Auto-start the Docker sandbox during backend startup when ACI is not configured:

- New service: `backend/app/services/docker_sandbox_service.py`
- Runs `docker compose up -d --build sandbox` on startup, polls `/health` until ready
- Stops the container on backend shutdown (only if we started it)
- Gated by `AUTO_START_SANDBOX` env var (default: `true`)
- Only activates when `USE_ACI_SANDBOX` is not `true`
- If sandbox is already running (manual start), skips startup and doesn't stop on shutdown

## Rules

- Never auto-start when ACI mode is enabled (production path untouched)
- If Docker isn't available, log at debug level and continue (sandbox-dependent features will fail gracefully via existing pre-flight check)
- First image build may take 2-3 minutes — timeout set to 300s for build, 90s for health
- `AUTO_START_SANDBOX=false` to opt out

## Files

- `backend/app/services/docker_sandbox_service.py` (new)
- `backend/app/main.py` (lifespan startup/shutdown)
- `backend/.env.example` (documented new env var)
