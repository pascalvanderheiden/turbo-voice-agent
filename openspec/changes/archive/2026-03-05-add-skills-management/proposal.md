# Change: Add Skills Management Agent with Marketplace Integration and Per-Project Skill Selection

## Why
Users cannot install, delete, or manage agent skills from the UI. The marketplace links on the agents page are broken (CORS), installed skills cannot be removed, and the Turbo Dev Agent does not leverage installed skills during code generation. A dedicated skills management capability — operated by an agent through the existing supervisor routing — would allow users to browse skills.sh, install skills via `npx skills add`, add local skills by copying them into the skills folder, remove skills, and receive real-time notifications for all operations. Additionally, the Dev Agent should intelligently select which installed skills to use per development project based on spec content.

## What Changes
- **Skills Agent**: New specialist agent registered in the supervisor, handling skill install/uninstall/search operations via function calling. Uses `npx skills` CLI commands executed in the background for marketplace installs, and file-copy for local installs.
- **Backend Endpoints**: REST API for skill management — install from marketplace (`npx skills add`), install from local path (copy to `.agents/skills/`), delete installed skill, search marketplace (`npx skills find`).
- **Frontend Agents Page**: Delete button on installed skill cards, working install button for marketplace skills, add-local-skill dialog, search marketplace via backend proxy (avoids CORS), real-time toast notifications for install/delete progress.
- **Per-Project Skill Selection**: DevTask model gains `skillIds` field. Dev task creation dialog shows installed skills as toggleable chips. Dev Agent injects selected skill content (from SKILL.md + references) into code generation prompts. Auto-suggestion based on spec content keywords.
- **Notifications**: All skill operations (install, delete, search) push notifications through the existing `NotificationProvider` system (toast + persistent panel).
- **Mobile**: Add skill management controls on agents screen and skill selection in dev task creation.

## Impact
- Affected specs: dev-service, web-app, agent-orchestration
- Affected code:
  - New: `backend/app/agents/skills_agent.py`, `backend/app/services/skills_service.py`
  - Modified: `backend/app/main.py` (new routes), `backend/app/agents/dev_agent.py` (skill injection), `backend/app/models/dev_task.py` (skillIds field)
  - Modified: `frontend/src/app/(app)/agents/page.tsx` (full skills management UI), `frontend/src/lib/api.ts` (skills API client)
  - Modified: `frontend/src/app/(app)/development/page.tsx` (skill selection in create dialog)
  - Modified: `mobile/app/agents.tsx`, `mobile/app/dev-list.tsx`, `mobile/src/lib/api.ts`
- **BREAKING**: DevTask model gains `skillIds` field (optional, defaults to empty list)
