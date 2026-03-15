## Why

The current Dev and Spec agents generate specs as free-form markdown and execute development pipelines entirely in-process using GPT-generated code written to temp directories. This approach lacks reproducibility, real developer tooling, and the ability to leverage GitHub Copilot CLI's agentic coding capabilities. By delegating code generation to a sandboxed GitHub Copilot CLI instance running in its own Container App, we gain real IDE-grade code generation, proper project scaffolding via OpenSpec CLI, and a secure execution environment. The spec format also needs restructuring — today's specs are verbose prose; instead they should produce two focused artifacts: a mockup description (frontend design brief) and an OpenSpec config (prompt instructions for the OpenSpec CLI workflow).

## What Changes

- **BREAKING**: Spec generation output format changes from free-form markdown to a two-part structure: (1) Mockup Description — concise frontend design description demonstrating key features, and (2) OpenSpec Config — focused prompt instructions starting with an `openspec-propose` for the foundation and one `openspec-propose` per feature.
- **BREAKING**: Dev pipeline replaces in-process GPT code generation with delegation to a GitHub Copilot CLI sandbox running in a separate Container App. The GitHub Copilot SDK (previously used for in-process code generation) is **removed** — all code generation is now delegated to GitHub Copilot CLI in the sandbox.
- **BREAKING**: The `gpt-5.3-codex` deployment (`DEV_CODEX_DEPLOYMENT`) is **removed**. The sandbox's Copilot CLI uses its own model selection (configurable per user on the Agent page), making the dedicated codex deployment obsolete.
- Two dev task modes renamed: **Mockup** (replaces current mock mode) and **OpenSpec** (replaces sequence mode). Both execute via the CLI sandbox.
- **Mockup mode**: CLI sandbox runs `openspec init` → `openspec-propose` with the mockup description → captures Playwright screenshots on completion. User can download generated code and view screenshots.
- **OpenSpec mode**: CLI sandbox runs `openspec init` → `openspec-propose` for foundation → `openspec-apply` → parallel `openspec-propose` per feature → `openspec-apply` each → Playwright screenshots. User can download code and view screenshots.
- Sandbox Container App provisioned via Bicep, running GitHub Copilot CLI in Docker sandbox (yolo mode).
- Skills synchronization: sandbox `/.copilot/skills` kept in sync with user's activated skills; sandbox recreated when skills change.
- Live streaming of CLI output to the frontend so users can watch GitHub Copilot CLI processing requests in real-time.
- One-time auth token connect flow added to profile settings page (similar to existing To-Do OAuth pattern) for authenticating the sandbox CLI.
- Agent page gains a new **Sandbox Config** section: model selection for GitHub Copilot CLI (default model changeable), sandbox status, and connection management.

## Capabilities

### New Capabilities
- `copilot-cli-sandbox`: Provisioning, lifecycle management, and communication with a dedicated Container App running GitHub Copilot CLI in Docker sandbox mode. Covers sandbox creation, skill sync, auth token injection, and real-time output streaming.
- `sandbox-auth`: One-time authentication token flow for connecting the GitHub Copilot CLI sandbox to the user's GitHub account, managed through profile settings.

### Modified Capabilities
- `spec-service`: Spec generation output changes from free-form markdown to two-part format (Mockup Description + OpenSpec Config). Spec model and generation prompts restructured.
- `dev-service`: Pipeline execution moves from in-process code generation to CLI sandbox delegation. Modes renamed to Mockup/OpenSpec. Pipeline stages replaced with sandbox command orchestration, Playwright screenshots, and code artifact download.
- `web-app`: Agent page updated with Sandbox Config section (model selection, sandbox status). Profile settings page extended with CLI auth token connection. Dev task UI updated for new Mockup/OpenSpec modes with live CLI output streaming, screenshot gallery, and code download.
- `azure-infrastructure`: New Container App for the GitHub Copilot CLI sandbox, including container image, networking, identity, and scaling configuration.

## Impact

- **Backend**: `spec_agent.py` — new generation prompts and output parsing. `dev_agent.py` — major rewrite replacing in-process pipeline with sandbox orchestration; remove all GitHub Copilot SDK usage. New `sandbox_service.py` for Container App management and CLI communication. New sandbox auth routes.
- **Frontend**: Agent page — new Sandbox Config section. Profile settings — auth token UI. Dev task views — live CLI streaming, screenshot viewer, code download.
- **Infrastructure**: New Bicep module for sandbox Container App. Updated backend Container App config for sandbox communication. New Cosmos DB container for sandbox state. **Remove** `DEV_CODEX_DEPLOYMENT` env var and associated AI Foundry deployment.
- **APIs**: New endpoints for sandbox management, auth token exchange, CLI output streaming (SSE/WebSocket), artifact download.
- **Dependencies**: Docker sandbox image for GitHub Copilot CLI, Playwright in sandbox for screenshots. **Remove** GitHub Copilot SDK dependency from backend.
