## Context

The Turbo Voice Agent platform includes a Dev Agent that generates prototype web applications from specs, and a Spec Agent that creates specifications from brainstormed ideas. Currently:

- **Spec Agent** generates free-form markdown specs via GPT prompts. These are human-readable but not machine-actionable — they can't drive automated tooling.
- **Dev Agent** executes a pipeline entirely in-process: GPT generates a plan, then GPT generates code, written to temp directories, started with a dev server, and screenshot-tested with Playwright. This produces inconsistent results and doesn't leverage real developer tooling.
- Both modes (mock/sequence) run inside the backend Container App's process, consuming its CPU/memory and creating security risks from executing arbitrary generated code.

The GitHub Copilot CLI now supports yolo mode (autonomous coding) and can be run in a Docker sandbox for security. OpenSpec CLI provides structured project scaffolding. Combining these gives us a production-grade code generation pipeline.

**Stakeholders**: End users (voice-driven app prototyping), platform operators (infrastructure), Dev Agent (orchestrator), Spec Agent (spec producer).

## Goals / Non-Goals

**Goals:**
- Replace in-process code generation with a sandboxed GitHub Copilot CLI running in a dedicated Container App
- Restructure spec output to produce two actionable artifacts: Mockup Description + OpenSpec Config
- Support two development modes: Mockup (quick visual prototype) and OpenSpec (full structured build)
- Enable real-time visibility into CLI execution from the frontend
- Provide secure GitHub authentication for the sandbox via a one-time token flow
- Keep sandbox skills in sync with the user's activated skills
- Allow users to select the default Copilot CLI model from the Agent page

**Non-Goals:**
- Multi-user sandbox sharing — each dev task gets its own sandbox instance
- Persistent sandbox state between tasks — sandboxes are ephemeral
- Supporting non-Next.js project types (current scope remains Next.js prototypes)
- Full CI/CD integration — this is prototyping, not production deployment
- Mobile app changes — web frontend only for this change

## Decisions

### 1. Sandbox as a separate Container App (not sidecar or in-process)

**Decision**: Provision a dedicated Container App for the GitHub Copilot CLI sandbox.

**Rationale**: Running code generation in-process is a security risk and resource contention issue. A sidecar would share the pod's resource limits. A separate Container App provides full isolation, independent scaling, and can be destroyed/recreated without affecting the backend.

**Alternatives considered**:
- *In-process (current)*: No isolation, security risk, resource contention. Rejected.
- *Sidecar container*: Better isolation but shares scaling/lifecycle with backend. Rejected.
- *Azure Container Instances (ACI)*: Per-task ephemeral containers — good isolation but higher latency to spin up, no persistent WebSocket. Rejected for latency.

### 2. Docker-in-Docker sandbox with yolo mode

**Decision**: Use the Docker sandbox pattern from [dev.to/brunoborges](https://dev.to/brunoborges/running-github-copilot-cli-safely-with-docker-sandbox-2f4i) — the Container App runs Docker, which hosts the Copilot CLI in a nested sandbox container per task.

**Rationale**: The Docker sandbox provides filesystem isolation per task. Yolo mode allows the CLI to execute without human confirmation prompts. Each task gets a clean workspace that can be destroyed after completion.

### 3. Spec format: Mockup Description + OpenSpec Config

**Decision**: Generated specs produce exactly two sections:
1. **Mockup Description**: A concise frontend design description (~200 words) covering layout, key components, interactions, and visual identity. Used by Mockup mode.
2. **OpenSpec Config**: A series of `openspec-propose` prompt instructions — one for the foundation, one per feature. Used by OpenSpec mode.

**Rationale**: The current free-form markdown is too verbose and not actionable. The two-part format maps directly to the two development modes. The Mockup Description is optimized for single-shot generation. The OpenSpec Config provides structured, iterative instructions for the CLI.

**Alternatives considered**:
- *Keep free-form markdown + post-processing*: Fragile extraction, inconsistent results. Rejected.
- *JSON schema*: Too rigid for creative spec content. Rejected.

### 4. Communication: Backend → Sandbox via HTTP API + SSE streaming

**Decision**: The sandbox Container App exposes an HTTP API. The backend sends task commands via POST requests. CLI output streams back via Server-Sent Events (SSE). The frontend connects to a backend SSE endpoint that proxies sandbox output.

**Rationale**: SSE is simpler than WebSocket for unidirectional streaming (CLI output is read-only for the user). HTTP for commands is stateless and retryable. The backend acts as a proxy to maintain auth boundaries.

**Alternatives considered**:
- *Direct WebSocket sandbox ↔ frontend*: Bypasses backend auth, exposes sandbox. Rejected.
- *Polling*: High latency for live output. Rejected.

### 5. Auth: One-time GitHub token via profile settings

**Decision**: Users provide a one-time GitHub personal access token or OAuth code via the profile settings page. The backend stores this encrypted in Cosmos DB (per-user) and injects it into the sandbox at task start via `gh auth login --with-token`.

**Rationale**: The sandbox needs GitHub authentication for Copilot CLI. Following the existing To-Do OAuth pattern (profile settings → store token → inject at use) provides a consistent UX. The token is scoped to `copilot` permissions only.

### 6. Skills sync: Recreate sandbox on skill change

**Decision**: When a user's activated skills change (install/uninstall), the sandbox is flagged for recreation. On next task trigger, a fresh sandbox is provisioned with the current skill set copied to `/.copilot/skills`.

**Rationale**: Skills affect Copilot CLI behavior significantly. Syncing incrementally is error-prone. Recreation is simple, reliable, and sandbox spin-up is fast (~10s with pre-pulled images).

### 7. Model selection stored per-user in profile

**Decision**: The default Copilot CLI model is stored in the user's profile in Cosmos DB. The Agent page exposes a Sandbox Config section with a model dropdown. The selected model is passed to the CLI via `--model` flag.

**Rationale**: Different users may prefer different models (speed vs quality). Per-user storage follows existing profile patterns. The Agent page is the natural home since it manages agent configuration.

## Risks / Trade-offs

- **[Container App cold start]** → Sandbox Container App may have cold start latency. Mitigation: Set min replicas to 1 for the sandbox, use pre-pulled Docker images.
- **[GitHub token security]** → Storing GitHub tokens in Cosmos DB creates a security surface. Mitigation: Encrypt at rest (Cosmos DB default), scope tokens minimally, support token rotation, auto-expire after configurable TTL.
- **[Sandbox resource consumption]** → Parallel feature builds in OpenSpec mode consume significant resources. Mitigation: Limit parallel builds to 3 concurrent, queue excess. Scale sandbox Container App independently.
- **[Copilot CLI version drift]** → CLI updates may break sandbox behavior. Mitigation: Pin CLI version in Docker image, test before updating.
- **[Skills sync race condition]** → User changes skills while a task is running. Mitigation: Snapshot skills at task start, ignore changes until next task.
- **[Network isolation]** → Sandbox needs outbound access (GitHub, npm) but should not access backend internals. Mitigation: Use Container App network policies, restrict ingress to backend only.

## Migration Plan

1. **Phase 1 — Infrastructure**: Deploy sandbox Container App via Bicep. No user-facing changes yet.
2. **Phase 2 — Backend services**: Implement `SandboxService`, update `SpecAgent` output format, refactor `DevAgent` pipeline.
3. **Phase 3 — Frontend**: Add Sandbox Config section to Agent page, auth token flow to profile settings, live CLI streaming and screenshot/download UI to dev task views.
4. **Phase 4 — Cutover**: Enable new pipeline, deprecate old in-process code generation. Old specs remain readable but new generation uses two-part format.

**Rollback**: Feature-flagged behind `USE_CLI_SANDBOX=true` env var. If disabled, falls back to existing in-process pipeline.

## Open Questions

- What specific GitHub token scopes are needed for Copilot CLI in the sandbox? (Likely `copilot` + `read:user`)
- Should sandbox Container App use a shared Docker image from ACR or pull from Docker Hub directly?
- What is the maximum concurrent sandbox task limit per user?
- Should generated code artifacts be stored in Azure Blob Storage or served directly from the sandbox filesystem before destruction?
