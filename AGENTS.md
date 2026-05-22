# Agent Notes — Turbo Voice Agent

This file is the short, agent-facing companion to `.github/copilot-instructions.md`. It captures the conventions that any AI coding assistant (Copilot, Squad, Claude, etc.) needs to be productive in this repo without re-reading the entire codebase.

## Architecture at a glance

```
Client (Web/iOS) ──WebSocket──▶ FastAPI ──▶ Voice Live API
                                  │
                                  ▼
                          SupervisorAgent
                                  │
       ┌───────────┬──────────────┼──────────────┬─────────────┐
       ▼           ▼              ▼              ▼             ▼
     Notes    Brainstorm      Research        Dev-task      Marketing
                                                  │
                                                  ▼
                              SessionSandboxClient (managed identity)
                                                  │
                                                  ▼
                         Azure Container Apps dynamic session pool
                         (per-taskId, Hyper-V isolated, prewarmed)
```

- **Backend** — Python 3.12+, FastAPI, service-layer pattern with Cosmos DB + in-memory dual implementations.
- **Web** — Next.js 15 (App Router), React 19, Tailwind v4, shadcn/ui.
- **Mobile** — Expo + React Native (iOS only, New Architecture mandatory).
- **Auth** — Entra ID; `AUTH_DISABLED=true` for local dev.
- **Sandbox** — `Microsoft.App/sessionPools` resource (Bicep: `infra/modules/session-pool.bicep`). Backend talks to it via `SessionSandboxClient` (`backend/app/services/session_sandbox_client.py`), keyed by `taskId`. Local dev: docker-compose `sandbox` service at `http://sandbox:3000`.

## How sandbox execution works

1. Dev-task starts → backend generates `taskId` (UUID).
2. `SessionSandboxClient.request(method, path, identifier=taskId, ...)` → `{SESSION_POOL_MANAGEMENT_ENDPOINT}{path}?identifier={taskId}&api-version=2025-02-02-preview` with `Authorization: Bearer <token>` from `DefaultAzureCredential` (scope `https://dynamicsessions.io/.default`).
3. First request only: backend adds `X-GH-Token: <user PAT>`. Sandbox middleware runs `gh auth login --with-token` and clears the in-process token.
4. Subsequent requests reuse the identifier → routed to the same sandbox container until pool cooldown.
5. On cancel / completion / disconnect: `client.stop_session(taskId, reason=...)`.

## Conventions

- **Service layer:** routes → service classes → Cosmos DB. Each service has `with_user(user_id)` for tenant isolation.
- **Dual implementations:** every service has a Cosmos class and an `InMemory*` fallback.
- **Module-level DI:** services initialized in `main.py` lifespan, stored as module globals, accessed via `_get_service()` helpers in route modules.
- **Cosmos auth:** `DefaultAzureCredential` in production; emulator (localhost/127.0.0.1) uses pre-shared key.
- **Ruff:** line-length=100, rules E/F/I/UP, target py312. Type hints on all public functions.
- **Commits:** Conventional Commits + `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer on AI-assisted work.
- **OpenSpec:** non-trivial changes go through `openspec/changes/` (propose → explore → implement → archive).
- **Squad:** `.squad/` holds optional multi-agent orchestration state. Vanilla Copilot works without it.

## Observability

`SessionSandboxClient` emits structured log records with `extra={}` fields:

| Event | Level | Fields |
| --- | --- | --- |
| `sandbox.session.allocated` | INFO | `identifier`, `latency_ms`, `status_code`, `retry_count` |
| `sandbox.session.request` | DEBUG | `identifier`, `method`, `path`, `status_code`, `latency_ms`, `retry_count` |
| `sandbox.session.error` | WARNING | `identifier`, `status_code`, `error_class`, `method`, `path` |
| `sandbox.session.stopped` | INFO | `identifier`, `status_code`, `reason` (`cancel` \| `complete` \| `disconnect`) |

Identifiers are dev-task UUIDs and safe to log. Tokens, PATs, and response bodies must never be logged.

App Insights is not currently wired into the backend lifespan; events with the `sandbox.` prefix in `record.event` can be re-emitted as `track_event` by adding an opencensus / `azure-monitor-opentelemetry` handler later. See `openspec/changes/sandbox-dynamic-sessions/design.md` for the rationale.

## Troubleshooting

See [`infra/README.md`](infra/README.md#troubleshooting) for the session-pool runbook (401/403 RBAC, 429 concurrency, probe failures, cold start).
