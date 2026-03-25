# Local Skill Installation to Disk

**Author:** Fenster  
**Date:** 2025-07-25  
**Status:** Implemented

## Decision

When running locally (no Azure Blob Storage), skill files are written directly to `.agents/skills/{skill-name}/` on the host filesystem. This directory is already volume-mounted into the Docker sandbox container at `/home/agent/.copilot/skills/:ro`, so skills become available immediately without container restarts.

## Implementation

- `InMemorySkillsService` gained `local_skills_dir: Path` parameter and `write_skill_files()` / `_delete_skill_dir()` helpers
- Marketplace skills download from GitHub → write to disk (same `_fetch_github_dir` logic as `CosmosSkillsService`)
- `upload_local_skills` endpoint in `dev.py` falls back to local disk write when `AZURE_STORAGE_ACCOUNT_NAME` is not set
- `deactivate_skill` removes the skill directory from disk
- `LOCAL_SKILLS_DIR` resolved from env var or `{project_root}/.agents/skills/`
- Azure path completely unchanged — blob storage + sandbox sync still works identically

## Rules

- Local disk writes only when `InMemorySkillsService` is active (no Cosmos/blob)
- Azure (Cosmos + blob) path is never modified — this is additive
- `.agents/skills/` is gitignored
- Best-effort sandbox `/skills/sync` call after local writes (for sandbox API awareness)

## Files

- `backend/app/services/in_memory_skills_service.py`
- `backend/app/main.py`
- `backend/app/routes/dev.py`
- `.gitignore`
