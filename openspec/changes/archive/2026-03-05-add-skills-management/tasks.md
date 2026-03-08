## 1. Backend — Skills Service
- [x] 1.1 Create `backend/app/services/skills_service.py` with `SkillsService` class
- [x] 1.2 Implement `list_installed()` — scan `.agents/skills/`, parse SKILL.md frontmatter (name, description, version)
- [x] 1.3 Implement `install_from_marketplace(repo, skill_name)` — run `npx skills add <repo> --skill <name> -y` as background subprocess, return immediately, resolve on completion
- [x] 1.4 Implement `install_from_local(source_path, name)` — copy directory to `.agents/skills/<name>/`, validate SKILL.md exists
- [x] 1.5 Implement `uninstall(name)` — remove `.agents/skills/<name>/` directory
- [x] 1.6 Implement `search_marketplace(query)` — run `npx skills find <query>`, parse CLI output into structured results (name, repo, url)
- [x] 1.7 Implement `get_skill_content(name, max_tokens)` — read SKILL.md + key reference files, truncate to token budget for prompt injection

## 2. Backend — Skills Agent
- [x] 2.1 Create `backend/app/agents/skills_agent.py` with `SkillsAgent` class
- [x] 2.2 Define tool functions: `install_skill`, `uninstall_skill`, `search_skills`, `list_skills`
- [x] 2.3 Register SkillsAgent in the supervisor routing (agent-orchestration)
- [x] 2.4 Add `skills` agent to `GET /api/agents/status` response

## 3. Backend — REST Endpoints
- [x] 3.1 Add `POST /api/agents/skills/install` — body: `{repo, skillName}`, triggers marketplace install, returns `{status: "installing", name}`
- [x] 3.2 Add `POST /api/agents/skills/install-local` — body: `{sourcePath, name}`, copies local dir, returns installed skill
- [x] 3.3 Add `DELETE /api/agents/skills/{name}` — removes skill directory, returns `{success: true}`
- [x] 3.4 Add `GET /api/agents/skills/search?q=<query>` — proxy to `npx skills find`, returns `{results: [{name, repo, url, description}]}`
- [x] 3.5 Update existing `GET /api/agents/skills` to use SkillsService (richer metadata)

## 4. Backend — Dev Agent Skill Injection
- [x] 4.1 Add `skillIds: list[str]` field to `DevTask` and `DevTaskCreate` models (optional, defaults to [])
- [x] 4.2 In `_run_mock_pipeline` and `_run_sequence_pipeline`, load selected skill content via `SkillsService.get_skill_content()`
- [x] 4.3 Append skill context to Plan and Build stage prompts (max ~2000 tokens per skill, max 3 skills total)
- [x] 4.4 Implement auto-suggest: given spec content, match keywords against installed skill descriptions and return top-3 relevant skill names
- [x] 4.5 Add `GET /api/dev/suggest-skills?specId=<id>` endpoint that returns suggested skillIds for a spec

## 5. Frontend — Agents Page Skills Management
- [x] 5.1 Replace hardcoded marketplace fallback with backend proxy search (`GET /api/agents/skills/search`)
- [x] 5.2 Add search input that queries backend on debounced input (300ms)
- [x] 5.3 Add "Install" button on marketplace skill cards — calls `POST /api/agents/skills/install`
- [x] 5.4 Add "Delete" button on installed skill cards with confirmation dialog
- [x] 5.5 Add "Add Local Skill" button with dialog (path input + name input)
- [x] 5.6 Show install/delete progress via toast notifications (using existing NotificationProvider)
- [x] 5.7 Auto-refresh skill list after install/delete completes
- [x] 5.8 Fix marketplace card links to use correct skills.sh URL format: `https://skills.sh/<owner>/<repo>/<skill-name>`

## 6. Frontend — Dev Task Skill Selection
- [x] 6.1 In dev task creation dialog, add "Skills" section showing installed skills as toggleable chips
- [x] 6.2 Call `GET /api/dev/suggest-skills?specId=<id>` when a spec is selected and pre-toggle suggested skills
- [x] 6.3 Pass selected `skillIds` in the create request body
- [x] 6.4 Show selected skills on dev task detail page header

## 7. Mobile — Skills Management
- [x] 7.1 Add skill management section on agents screen (install marketplace, delete, add local)
- [x] 7.2 Add skill selection chips in dev task creation flow
- [x] 7.3 Show selected skills on dev detail screen

## 8. Validation
- [x] 8.1 Test marketplace search via backend proxy (verify `npx skills find` parsing)
- [x] 8.2 Test marketplace install end-to-end (`npx skills add` completes and skill appears in list)
- [x] 8.3 Test local skill install (copy from local path)
- [x] 8.4 Test skill deletion
- [x] 8.5 Test dev task creation with skill selection
- [x] 8.6 Verify skill content is injected into dev agent prompts
- [x] 8.7 Run `npm run build` for frontend
- [x] 8.8 Run `npx expo export --platform ios` for mobile
- [x] 8.9 Verify notifications appear for skill install/delete operations
