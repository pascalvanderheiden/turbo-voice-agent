## Context

The current skills management system involves a multi-layer file distribution pipeline: skills are downloaded from GitHub repos via the skills.sh marketplace API, stored on the backend filesystem (`.agents/skills/`), persisted to Azure Blob Storage, synced back on container restart, and then packaged as tar.gz archives to upload into the sandbox container. This architecture was built incrementally but has proven fragile — shell argument limits, base64 encoding overflows, blob sync timing, and mkdir failures have caused repeated production issues.

The skills.sh marketplace provides an `npx @anthropic/skills install <skill>` command that the Copilot CLI natively understands. Skills installed this way are placed directly into `.github/skills/` in the workspace. By running these npx commands inside the sandbox container (which already has npm/npx), we eliminate the entire file distribution pipeline.

**Current state**: SkillsService → BlobSkillsStorage → CosmosSkillsService → tar.gz → sandbox `/files/upload`  
**Target state**: Cosmos DB (activation metadata + npx command) → sandbox runs npx commands directly

## Goals / Non-Goals

**Goals:**
- Simplify skills to an activate/deactivate toggle backed by Cosmos DB metadata only
- Store the npx install command per skill so the sandbox can run it directly
- Remove all filesystem-based skill storage from the backend (no `.agents/skills/`, no blob)
- Remove `blob_skills_storage.py` and blob sync logic from `CosmosSkillsService`
- Replace tar.gz upload in dev agent with npx command execution in sandbox
- Stream skill installation progress to frontend for visibility
- Maintain the existing search + browse marketplace UX

**Non-Goals:**
- Custom/private skill repositories (only skills.sh marketplace for now)
- Skill version pinning or lock file management
- Caching npx-installed skills across sandbox sessions (fresh install each time is acceptable)
- Changes to how Copilot CLI reads skills from `.github/skills/` (that's upstream)

## Decisions

### 1. Cosmos DB stores activation state + npx command (no files)

**Decision**: Each activated skill is a Cosmos DB document with the skill's name, description, source repo, and the exact npx install command to run in the sandbox.

**Rationale**: The npx command is the single source of truth. We don't need files on the backend — the sandbox fetches them directly from npm/GitHub at runtime. This eliminates blob storage, filesystem sync, and tar.gz packaging entirely.

**Alternative considered**: Cache skill files in a shared volume mounted by both backend and sandbox. Rejected because it couples the containers and doesn't simplify the architecture meaningfully.

### 2. Skills installed via sandbox shell commands (not HTTP upload)

**Decision**: The dev agent sends each skill's npx install command as a shell command to the sandbox via the existing `POST /tasks` endpoint (same as other shell commands). Output is streamed to the frontend.

**Rationale**: The sandbox already supports shell command execution with streaming output. Using the same mechanism for skill installation provides visibility and consistency. No new endpoints needed.

**Alternative considered**: Keep the `PUT /files/upload` endpoint for a pre-built skill cache. Rejected because it maintains the complexity we're trying to remove.

### 3. Frontend uses "Activate"/"Deactivate" terminology

**Decision**: Replace "Install"/"Uninstall" with "Activate"/"Deactivate" in the UI. The marketplace search and browse experience stays the same.

**Rationale**: Skills are not downloaded to the user's machine anymore. "Activate" better reflects that we're bookmarking a skill for use in sandboxes. The mental model shifts from "I have these files" to "I use these skills".

### 4. Skill context for prompt injection fetched from SKILL.md via npx or marketplace API

**Decision**: The `_get_skill_context()` method in the dev agent will no longer read local files. Instead, skill content for prompt injection will be fetched from the skills.sh API (which returns SKILL.md content) at task creation time, or cached in the Cosmos activation document.

**Rationale**: Without local files, we need another source for skill content used in prompt injection. The marketplace API already has this data. Caching it in Cosmos avoids repeated API calls.

### 5. Remove `PUT /files/upload` endpoint from sandbox

**Decision**: Remove the tar.gz upload endpoint since it was only used for skills. If future needs arise for file uploads, it can be re-added.

**Rationale**: Reduces attack surface and simplifies sandbox server code.

## Risks / Trade-offs

**[Risk] Sandbox requires internet access for npx install** → Sandbox containers in Azure Container Apps already have outbound internet access. If network policies change, skills won't install. Mitigation: monitor for failures and alert.

**[Risk] npx install adds latency to pipeline startup** → Each skill install takes 5-15 seconds (npm fetch + extract). With 3 skills, that's 15-45 seconds added. Mitigation: Run skill installs in parallel if possible, or accept the tradeoff given the massive simplification.

**[Risk] skills.sh API availability** → If skills.sh is down, search won't work and npx commands may fail. Mitigation: Cosmos caches activation data, so existing activations still work. Only new activations require the API.

**[Risk] Breaking change for existing users** → Users with locally uploaded skills lose them. Mitigation: skills-lock.json still exists as reference. Communicate the change and guide re-activation from marketplace.

**[Trade-off] Fresh install each sandbox session** → Skills are not cached between dev tasks. Each pipeline run re-downloads. Acceptable because sandbox workspaces are ephemeral anyway, and npm caching helps with repeated installs.
