## Why

Custom skills installed via skill management are stored on the backend (filesystem + Blob Storage) but never copied into the sandbox container. The Copilot CLI inside the sandbox can only use built-in OpenSpec skills — user-installed skills are invisible. This means dev pipelines cannot leverage custom skills the user has configured.

## What Changes

- Copy user-installed skills from `.agents/skills/` into the sandbox Docker image at build time
- The sandbox Dockerfile will include a `COPY` step for the skills directory into `/home/agent/.copilot/skills/`
- Docker Compose will add a volume mount from the host `.agents/skills/` to the sandbox container
- Skills are refreshed on sandbox rebuild (not at runtime)

## Capabilities

### New Capabilities
- `sandbox-skill-mount`: Build-time and volume-mount mechanism to make user-installed skills available inside the sandbox container

### Modified Capabilities
- `copilot-cli-sandbox`: The sandbox container now includes user skills at `/home/agent/.copilot/skills/`

## Impact

- `sandbox/Dockerfile` — new COPY step for skills directory
- `docker-compose.yml` — new volume mount for `.agents/skills/`
- `infra/modules/container-app-sandbox.bicep` — may need Azure Files or init container for Azure deployment
- Dev pipelines gain access to custom skills without code changes to `dev_agent.py`
