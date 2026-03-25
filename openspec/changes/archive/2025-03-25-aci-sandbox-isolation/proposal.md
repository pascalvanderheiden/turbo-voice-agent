## Why

The dev-task sandbox currently runs as a single shared Azure Container App (2 CPU, 4GB RAM, `maxReplicas: 1`). All dev-tasks share one Node.js process with directory-level isolation (`/workspace/{task_id}`). This causes resource contention (one heavy `npm install` starves other tasks), is a single point of failure (crash kills all active tasks), cannot scale horizontally (in-memory task state), and has no kernel-level isolation between tasks. Moving to Azure Container Instances (ACI) gives each dev-task its own ephemeral container with true process/network/filesystem isolation, independent resource limits, and pay-per-use billing.

## What Changes

- **New**: ACI container group lifecycle manager in the backend — provisions a dedicated sandbox container per dev-task on demand, tears it down on completion
- **New**: Bicep module for ACI infrastructure (subnet, managed identity, container image config)
- **Modified**: Backend `dev_agent.py` — instead of calling a fixed `SANDBOX_URL`, resolve the per-task ACI endpoint dynamically
- **Modified**: Backend `routes/dev.py` — live preview proxy and file download route to per-task ACI endpoint
- **Modified**: Skills sync — skills must be mounted/synced per-container instead of relying on a persistent `/home/agent/.copilot/skills` volume
- **Removed**: `container-app-sandbox.bicep` — the always-on shared sandbox Container App is replaced by on-demand ACI instances
- **Modified**: `azure.yaml` — remove sandbox as a persistent service, add ACI image build target

## Capabilities

### New Capabilities
- `aci-sandbox-lifecycle`: Manage per-task ACI container group creation, health polling, URL resolution, and teardown
- `aci-sandbox-infra`: Bicep infrastructure for ACI — subnet in existing VNet, managed identity, ACR pull role, NSG rules

### Modified Capabilities
- `copilot-cli-sandbox`: Sandbox server.js and Dockerfile remain mostly the same, but entrypoint changes (single-task mode, no persistent state, pre-loaded skills from blob at startup)
- `sandbox-skill-mount`: Skills loaded from blob storage at container startup instead of hot-reload to a persistent volume
- `sandbox-auth`: ACI containers need managed identity for blob storage and ACR access

## Impact

- **Infrastructure**: New Bicep modules for ACI + VNet subnet; remove `container-app-sandbox.bicep`. VNet integration required for backend↔ACI private communication.
- **Backend**: `dev_agent.py` needs ACI lifecycle client (create/poll/delete). `_sandbox_exec` resolves sandbox URL per-task. New `aci_sandbox_service.py` service layer.
- **Sandbox image**: Same Docker image, minor entrypoint changes for single-task mode. Published to existing ACR.
- **Cost**: Moves from always-on (2 CPU × 24/7 ≈ $90/mo) to pay-per-use (billed per vCPU-second + GB-second while task runs). Cheaper at low-to-moderate usage, comparable at high usage.
- **Latency**: Cold-start penalty of ~30-60s for ACI container group creation. Mitigated by starting ACI provisioning early (on task creation, before init stage).
- **CI/CD**: `azd deploy` no longer deploys a sandbox service. ACI containers use the latest image from ACR at creation time.
- **Skills**: No more hot-reload endpoint — skills baked in at container start via `sync-skills.sh`. Marketplace skill activation takes effect on next task (not mid-task).
