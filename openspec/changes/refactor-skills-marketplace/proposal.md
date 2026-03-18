## Why

Skills management currently requires downloading skill files from GitHub, storing them on disk and in Azure Blob Storage, then packaging them as tar.gz archives to upload into the sandbox container. This multi-step process is fragile (shell argument limits, base64 encoding issues, blob sync failures) and adds operational complexity. The skills.sh marketplace already provides an `npx` install command that Copilot CLI natively supports — we should use it directly in the sandbox instead of re-implementing file distribution ourselves.

## What Changes

- **BREAKING** Remove local file upload for skills (no more drag-and-drop folder upload)
- **BREAKING** Remove Azure Blob Storage for skill file persistence (no more blob sync on startup)
- **BREAKING** Remove tar.gz upload of skill files to sandbox (`PUT /files/upload` endpoint removed for skills)
- Replace "install" with "activate/deactivate" — skills are toggled on/off, not downloaded to the backend
- Store the `npx` install command from skills.sh marketplace in Cosmos DB per activated skill
- In sandbox pipeline: after `openspec init`, run each activated skill's `npx` command to install it directly via the Copilot CLI skill system
- Stream skill activation output to the frontend for visibility
- Simplify `SkillsService` to only manage activation state (no filesystem operations)
- Remove `blob_skills_storage.py` entirely
- Remove `CosmosSkillsService` blob sync logic — Cosmos stores only activation metadata + npx command

## Capabilities

### New Capabilities
- `skill-activation`: Activate/deactivate skills from the skills.sh marketplace. Store npx install command per skill. No file management — skills are installed directly in the sandbox at runtime via their npx command.
- `sandbox-skill-install`: During dev task pipeline, run npx install commands for each activated skill in the sandbox container. Stream output showing which skills are being installed. Replace the current tar.gz upload approach.

### Modified Capabilities

_(none — no existing spec-level requirements are changing)_

## Impact

- **Backend services**: `skills_service.py` simplified (remove filesystem ops), `cosmos_skills_service.py` rewritten (remove blob sync), `blob_skills_storage.py` deleted
- **Backend routes**: Remove upload-local, install-local endpoints. Simplify install to just activate (store npx command). Uninstall becomes deactivate.
- **Backend dev agent**: `_install_skills_in_sandbox()` rewritten to run npx commands instead of tar.gz upload. `_get_skill_context()` may need to fetch content differently (or be removed if npx install handles it).
- **Frontend**: Remove local upload UI. Rename "Install"/"Uninstall" to "Activate"/"Deactivate". Remove file count display.
- **Infrastructure**: Can remove blob storage container for skills. Simplifies Azure resource footprint.
- **Sandbox**: `PUT /files/upload` endpoint can be simplified (only used for skills currently). npx must be available in sandbox (already is).
- **Model**: Skill metadata in Cosmos changes — add `npxCommand` field, remove `fileCount`, `source` path references.
