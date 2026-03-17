## Context

Skills are installed via the backend skill management UI and stored in `.agents/skills/` on the host filesystem (local dev) or Azure Blob Storage (production). The sandbox container is a separate Docker image that runs the Copilot CLI. Currently, the container only has built-in OpenSpec skills created during `openspec init` at startup — no bridge exists to the backend's skill store.

The user has confirmed that skills only need to be available after a sandbox rebuild — no runtime hot-reload required.

## Goals / Non-Goals

**Goals:**
- Make user-installed skills available inside the sandbox at `/home/agent/.copilot/skills/`
- Local dev: volume mount from host `.agents/skills/` into the container
- Azure: copy skills from Blob Storage into the sandbox image or use an init step

**Non-Goals:**
- Runtime skill hot-reload (rebuild is acceptable)
- Skill deduplication or conflict resolution with built-in OpenSpec skills
- Per-user skill isolation in the sandbox (single-tenant sandbox)

## Decisions

### 1. Local dev: Docker Compose bind mount
**Decision:** Add a bind mount `.agents/skills/:/home/agent/.copilot/skills/:ro` to the sandbox service in `docker-compose.yml`.

**Rationale:** Simple, zero-copy, reflects host changes on next container restart. Read-only mount prevents the sandbox from modifying the skill store.

**Alternative:** COPY in Dockerfile — rejected because it requires a full image rebuild for every skill change, while a bind mount just needs a container restart.

### 2. Sandbox Dockerfile: create the skills target directory
**Decision:** Add `RUN mkdir -p /home/agent/.copilot/skills && chown agent:agent /home/agent/.copilot/skills` to the Dockerfile.

**Rationale:** Ensures the mount point exists with correct ownership even when no skills are installed yet.

### 3. Azure: download skills from Blob Storage during entrypoint
**Decision:** Add an init step in `sandbox/entrypoint.sh` that downloads skills from Azure Blob Storage (if `AZURE_STORAGE_ACCOUNT_NAME` is set) before starting the server.

**Rationale:** Azure Container Apps don't support host bind mounts. An init download at container start is the simplest approach that doesn't require Azure Files or shared volumes. Since skills only refresh on rebuild/restart, this is acceptable.

**Alternative:** Azure Files shared volume — adds infrastructure complexity (new Bicep resource, mount config). Overkill for a directory that rarely changes.

### 4. Skills directory structure
**Decision:** Skills are placed at `/home/agent/.copilot/skills/<skill-name>/` mirroring the `.agents/skills/` layout on the host.

**Rationale:** This is where the Copilot CLI looks for user-level skills.

## Risks / Trade-offs

- **[Empty mount on first run]** → If `.agents/skills/` doesn't exist on the host, Docker will create an empty directory. The sandbox still works — just no custom skills. Mitigated by `mkdir -p` in Dockerfile.
- **[Azure blob download latency]** → Downloading skills at container start adds a few seconds to startup. Acceptable since sandbox starts infrequently.
- **[Stale skills in Azure]** → Skills downloaded at startup won't update until the container restarts. This matches the user's requirement (refresh on rebuild only).
