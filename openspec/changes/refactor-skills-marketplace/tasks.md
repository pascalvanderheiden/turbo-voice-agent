## 1. Backend Model & Schema

- [x] 1.1 Update Cosmos DB skill document schema: add `npxCommand` field, remove `fileCount` field. Update any Pydantic models in `backend/app/models/` if a skill model exists, otherwise define the schema in the service.
- [x] 1.2 Create a database migration or upsert logic to handle existing skill documents (add `npxCommand`, remove stale fields).

## 2. Backend Skills Service Rewrite

- [x] 2.1 Rewrite `backend/app/services/skills_service.py`: remove all filesystem operations (`list_installed`, `install_from_local`, `install_from_upload`, `uninstall` file deletion, `get_skill_content` file reading). Keep `search_marketplace` (skills.sh API call).
- [x] 2.2 Rewrite `backend/app/services/cosmos_skills_service.py`: remove blob sync logic (`sync_from_blob`, `persist_skill`, `remove_skill_data` blob calls). Replace with pure Cosmos DB CRUD: `activate_skill(name, description, source, npx_command)`, `deactivate_skill(name)`, `list_activated()`, `get_skill(name)`.
- [x] 2.3 Delete `backend/app/services/blob_skills_storage.py` entirely.
- [x] 2.4 Update `backend/app/services/cosmos_skills_service.py` to cache skill description/content from marketplace API in the Cosmos document at activation time (for prompt injection in `_get_skill_context()`).

## 3. Backend API Routes

- [x] 3.1 Remove `/api/agents/skills/install-local` endpoint from `backend/app/main.py`.
- [x] 3.2 Remove `/api/agents/skills/upload-local` endpoint from `backend/app/main.py`.
- [x] 3.3 Rename `/api/agents/skills/install` to activate semantics: accept `{repo, skillName, npxCommand, description}`, store activation in Cosmos DB (no file download).
- [x] 3.4 Rename `/api/agents/skills/{name}` DELETE to deactivate semantics: remove Cosmos document only.
- [x] 3.5 Update `/api/agents/skills` GET to return activated skills from Cosmos DB (not filesystem scan).
- [x] 3.6 Keep `/api/agents/skills/search` GET unchanged (skills.sh API proxy).

## 4. Dev Agent — Sandbox Skill Installation

- [x] 4.1 Rewrite `_install_skills_in_sandbox()` in `backend/app/agents/dev_agent.py`: instead of tar.gz upload, iterate through task's skill_ids, look up each skill's `npxCommand` from Cosmos, and execute it as a shell command in the sandbox via `_sandbox_exec()`.
- [x] 4.2 Add stream output headers (`── install-skill-<name> ──`) before each npx command for visibility.
- [x] 4.3 Ensure skill install failures are non-blocking (log + continue, don't abort pipeline).
- [x] 4.4 Update `_get_skill_context()` to read skill content from Cosmos DB `description`/`content` field instead of local filesystem.
- [x] 4.5 Remove the tar.gz creation logic and httpx PUT calls from `_install_skills_in_sandbox()`.

## 5. Sandbox Server Cleanup

- [x] 5.1 Remove `PUT /files/upload` endpoint from `sandbox/server.js`.
- [x] 5.2 Verify `GET /files` and `GET /files/*` endpoints still work (needed for screenshot collection).

## 6. Frontend — Skills Management UI

- [x] 6.1 Update `frontend/src/app/(app)/agents/page.tsx`: rename "Install" button to "Activate", "Uninstall"/"Delete" to "Deactivate".
- [x] 6.2 Remove local upload dialog and file picker UI from the agents page.
- [x] 6.3 Update installed skills display: remove file count, show source repo and activation date instead.
- [x] 6.4 Update the install flow to pass `npxCommand` from marketplace search results to the activate endpoint.

## 7. Frontend API Client

- [x] 7.1 Update `frontend/src/lib/api.ts` `skillsApi` object: remove `uploadLocal` method, update `install` to `activate` with new payload shape `{repo, skillName, npxCommand, description}`, rename `delete` to `deactivate`.
- [x] 7.2 Update `InstalledSkill` TypeScript interface: add `npxCommand`, `activatedAt` fields, remove `fileCount`.

## 8. Cleanup & Infrastructure

- [ ] 8.1 Remove blob storage container reference for skills from Bicep infra if explicitly created for skills.
- [x] 8.2 Remove `skills-lock.json` from repo root (no longer needed — activation state is in Cosmos).
- [x] 8.3 Update `backend/app/main.py` lifespan: remove blob sync on startup, remove `BlobSkillsStorage` initialization.
- [x] 8.4 Clean up unused imports across all modified files.

## 9. Testing & Validation

- [x] 9.1 Run existing backend tests, fix any broken by service interface changes.
- [ ] 9.2 Manually test: search marketplace → activate skill → create dev task → verify npx command runs in sandbox stream → skill visible in Copilot CLI.
- [ ] 9.3 Verify deactivation removes skill from Cosmos and future dev tasks don't include it.
- [ ] 9.4 Verify pipeline completes successfully with 0 skills, 1 skill, and 3 skills activated.
