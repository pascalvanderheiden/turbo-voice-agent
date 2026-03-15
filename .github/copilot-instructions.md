# Copilot Instructions — Turbo Voice Agent

## Architecture

Real-time conversational AI voice agent with multi-agent orchestration:

```
Client (Web/iOS) → WebSocket → FastAPI → Voice Live API (speech-to-speech)
                                  ↓
                            SupervisorAgent → routes to specialist agents
                                  ↓
                    Notes | Brainstorm | Research | Spec | Dev | Marketing | Skills
                                  ↓
                            Cosmos DB (per-user tenant isolation)
```

- **Backend**: Python 3.12+ / FastAPI — service layer pattern with dual Cosmos DB + in-memory implementations
- **Web frontend**: Next.js 15 (App Router), React 19, Tailwind CSS v4, shadcn/ui (new-york style), Tabler Icons
- **Mobile**: React Native 0.82+ / Expo SDK 52+ (New Architecture mandatory, iOS only)
- **Auth**: Azure Entra ID (JWT validation on backend, MSAL on frontend). `AUTH_DISABLED=true` for local dev
- **Infrastructure**: Bicep IaC, Azure Container Apps, deployed via `azd up`

## Build, Test, and Lint

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test
pytest tests/test_notes_service.py::test_create_note -v

# Lint
ruff check .
ruff format .

# Dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

npm run dev          # Dev server on :3000
npm run build        # Production build
npm run lint         # ESLint

# E2E tests (Playwright)
npx playwright test
npx playwright test e2e/mobile-navigation.spec.ts   # Single file
```

### Mobile

```bash
cd mobile
npm install
npx expo start --ios
```

### Infrastructure

```bash
docker compose up -d                    # Start Cosmos DB emulator
azd auth login && azd up                # Deploy to Azure
```

## Key Conventions

### Backend patterns

- **Service layer**: Routes → service classes → Cosmos DB. Each service has `with_user(user_id)` for tenant isolation.
- **Dual implementations**: Every service has a Cosmos DB class and an `InMemory*` fallback (e.g., `NotesService` / `InMemoryNotesService`).
- **Module-level DI**: Services initialized in `main.py` lifespan, stored as module globals, accessed via `_get_service()` helpers in route modules. Not a DI container.
- **Agent architecture**: 9 specialist agents + 1 SupervisorAgent. Each agent exposes `tool_definitions` (list of function schemas). Supervisor routes function calls by matching function name to agent's `handle_function_call()`.
- **Cosmos DB dual auth**: `DefaultAzureCredential` in production (managed identity, no API keys). Emulator detected by `localhost`/`127.0.0.1` in endpoint → uses pre-shared key.
- **Ruff config**: line-length=100, rules E/F/I/UP, target py312. Type hints on all public functions.

### Frontend patterns

- **Auth**: MSAL wraps the app (`auth-provider.tsx`). `authFetch()` in `lib/api.ts` auto-attaches Bearer tokens.
- **API client**: Typed functions in `lib/api.ts` organized as namespaced objects (`notesApi.list()`, `ideasApi.refine()`).
- **Voice hook**: `lib/use-voice-session.ts` manages WebSocket lifecycle, PCM16 audio I/O, function call events, and background task notifications.
- **Components**: Server Components by default; Client Components only when needed. Modular folders: `layout/`, `voice/`, `notes/`, `ui/`.

### Voice integration

- WebSocket endpoint `/ws/voice` proxies audio between client and Azure Voice Live API.
- Token passed as query param for WebSocket auth.
- Function calling during voice sessions: Voice Live triggers tool calls → `function_handler.py` executes → result injected into voice stream.
- Long-running tools (research, spec generation, video) run as background tasks via `background_tasks.py`.
- Supports EN and NL language configs via `get_voice_config(lang=)`.

### Git workflow

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`
- Always include `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` on AI-assisted commits
- Use OpenSpec workflow (in `openspec/`) for new features — propose → explore → implement → archive

### Branding

- **Turbo Agent** identity: hot pink `#E91E8C`, cyan `#00D4FF`, purple `#7B2FBE`
- Dark mode is default (`#0F0F1A` base). Light mode is secondary.
- Typography: Inter (UI) + JetBrains Mono (code)

## CI/CD

GitHub Actions workflow (`.github/workflows/deploy.yml`) triggers on push to `main`:

- **Only `backend/` or `frontend/` changed** → `azd deploy` (rebuild & redeploy containers only)
- **`infra/` or `azure.yaml` changed** → `azd provision` + `azd deploy` (full infrastructure update)
- **Manual trigger (`workflow_dispatch`)** → full provision + deploy

Uses OIDC federated credentials (no stored secrets). Requires GitHub repository variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_ENV_NAME`, `AZURE_LOCATION`, plus Bicep parameters (`ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `CUSTOM_DOMAIN_NAME`, `EXISTING_CERT_NAME`, `DEPLOYER_PRINCIPAL_ID`).

## Environment Setup

Backend needs `backend/.env` (copy from `.env.example`). Key vars: `COSMOS_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, `VOICE_LIVE_ENDPOINT`. Set `AUTH_DISABLED=true` for local dev without Entra ID.

Frontend needs `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.

Cosmos DB emulator runs via `docker compose up -d` on port 8081. Production uses managed identity — all `*_API_KEY` vars are omitted.
