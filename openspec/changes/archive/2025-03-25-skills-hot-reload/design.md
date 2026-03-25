## Context

The sandbox is a single-replica Container App running the Copilot CLI. Skills live at `/home/agent/.copilot/skills/` and are synced from Azure Blob Storage at container startup via `entrypoint.sh`. Currently, every dev-task pipeline has a "skills" stage that re-runs the blob sync (`_install_skills_in_sandbox`) plus a verification prompt (`_verify_skills_in_sandbox`) — adding ~30-60s latency and consuming a premium Copilot request per task.

The sandbox already has blob sync at startup. The only gap is skills activated *after* the container started. This can be solved by adding a push endpoint to the sandbox server.

## Goals / Non-Goals

**Goals:**
- Skills become available in the sandbox within seconds of activation (hot reload)
- Remove the per-task "skills" pipeline stage entirely
- Save one premium Copilot request per task (verify-skills removal)
- Skills deactivation removes files from the sandbox immediately

**Non-Goals:**
- Multi-tenant skill isolation (sandbox is single-user, single-replica)
- Skill versioning or rollback
- Changing how skills are stored in blob storage (that part works fine)

## Decisions

**Decision 1: Push endpoint on sandbox vs. polling**
- **Choice**: Add `POST /skills/sync` to sandbox server that backend calls after activation
- **Alternative**: Sandbox polls blob storage periodically
- **Rationale**: Push is instant and doesn't waste resources. The backend already knows the sandbox URL (`SANDBOX_URL` env var) and makes HTTP calls to it for task execution.

**Decision 2: Full re-sync vs. individual skill push**
- **Choice**: Single `POST /skills/sync` endpoint that re-syncs all skills from blob
- **Alternative**: Push individual skill files via `POST /skills/push` with file content
- **Rationale**: Full re-sync is simpler, reuses the existing entrypoint logic, and handles edge cases (e.g., blob updated but push failed). Individual push would be faster for single-skill activation but adds complexity. The full sync takes <5s for typical skill counts.

**Decision 3: Remove skills pipeline stage entirely vs. make it a no-op**
- **Choice**: Remove the stage from pipeline definitions and UI
- **Alternative**: Keep stage but skip execution (instant "completed")
- **Rationale**: The stage adds visual noise and implies work is happening. Clean removal is clearer. If a skill is somehow missing, the Copilot CLI will simply not have it — same as if it failed to sync today.

## Risks / Trade-offs

- **[Risk] Sandbox unreachable during activation** → Skill is still in blob storage. Next container restart picks it up. Log a warning but don't fail the activation.
- **[Risk] Race condition: task starts before sync completes** → Unlikely since sync takes <5s and tasks are user-initiated. Acceptable risk.
- **[Risk] Entrypoint sync + hot-reload sync overlap** → The `az storage blob download` command uses `--overwrite`, so concurrent syncs are safe (idempotent).
