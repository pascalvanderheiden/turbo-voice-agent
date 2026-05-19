# Personal Reference Audit

## Scope
Cross-repo audit for maintainer-identifying references and GUID-like values, excluding generated directories (`.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `.next`).

## Findings

| File | Line | Kind | Finding | Proposed action | Owner |
| --- | ---: | --- | --- | --- | --- |
| `.squad/config.json` | 3 | local path | Maintainer username appeared inside `teamRoot` absolute path. | Replace with generic placeholder path. | Keaton |
| `.squad/team.md` | 28 | name | Maintainer name appeared in seeded project context. | Replace with `Project Maintainer`. | Keaton |
| `.squad/agents/keaton/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/fenster/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/hockney/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/verbal/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/redfoot/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/kobayashi/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/agents/mcmanus/history.md` | 6 | name | Seeded maintainer reference in agent history header. | Replace with `the project maintainer`; keep later learnings intact. | Keaton |
| `.squad/decisions.md` | 78 | name | Active decision author used the maintainer's full name. | Replace with `Project Maintainer`. | Keaton |
| `.squad/decisions/inbox/copilot-directive-2026-05-19-opensource-decisions.md` | 2, 4, 6, 7 | name | Decision note used the maintainer name in attribution and narrative. | Replace direct identifier with `the maintainer`. | Keaton |
| `.squad/log/2026-05-19T12:01:41Z-archive-optimize-slides-pipeline.md` | 24 | name | Historical log contained a `Requested by:` maintainer name. | Scrub request attribution only. | Keaton |
| `.squad/orchestration-log/2026-05-19T12:45:19Z-redfoot.md` | 5, 17 | name | Orchestration log exposed maintainer identity in request attribution and review note. | Replace with neutral maintainer wording. | Keaton |
| `openspec/changes/open-source-project/proposal.md` | 35 | policy text | Proposal still said `.squad/` was not part of OSS distribution. | Update proposal to match approved keep-and-anonymize decision. | Keaton |
| `openspec/changes/open-source-project/design.md` | 15, 17, 35, 67, 68, 91, 147, 229, 273 | name / policy text | Design still referenced the maintainer directly and reflected the pre-approval `.squad/` decision. | Anonymize maintainer references and update `.squad/` handling language. | Keaton |
| `openspec/changes/open-source-project/tasks.md` | 3-11, 95-98 | name / task text | Task text still embedded maintainer-specific search strings and unchecked Keaton-owned tasks. | Genericize wording and mark completed Keaton-owned tasks. | Keaton |
| `.squad/skills/backend-oss-scrub/SKILL.md` | 7 | name | Backend scrub playbook still named the maintainer username explicitly. | Generalize the guidance to maintainer identifiers. | Keaton |
| `infra/modules/rbac.bicep` | 32-36, 183 | GUID | Azure built-in role definition IDs detected by generic GUID sweep. | No scrub needed; document as intentional false positives. | Verbal |
| `infra/modules/aci-identity.bicep` | 18-19 | GUID | Azure built-in role definition IDs detected by generic GUID sweep. | No scrub needed; document as intentional false positives. | Verbal |
| `infra/modules/aci-backend-role.bicep` | 9 | GUID | Azure built-in Contributor role ID detected by generic GUID sweep. | No scrub needed; document as intentional false positives. | Verbal |
| `azure.yaml` | n/a | manual audit | No maintainer-specific name, domain, or GUID found during manual review. | No change needed. | Verbal |
| `.github/workflows/deploy.yml` | n/a | manual audit | No hardcoded maintainer identifiers found; values already flow through `vars.*` / `secrets.*`. | No change needed. | Verbal |
| `backend/.env.example` | n/a | manual audit | No maintainer-specific names found in backend env example; placeholder endpoints are generic. | No change needed. | Fenster |
| `frontend/.env.example` | n/a | manual audit | No maintainer-specific names found in frontend env example. | No change needed in this pass. | McManus |

## Notes
- `.squad/agents/*/charter.md` was reviewed and did not contain maintainer-identifying content.
- `.squad/casting/registry.json` and `.squad/casting/history.json` were reviewed and did not contain maintainer-identifying content.
- README currently does not require `.squad/`, but it still needs a short explanatory note from the docs/frontend slice so OSS users know it is optional metadata.

## POST-SCRUB VERIFICATION
- 2026-05-19 Keaton verification grep (excluding generated directories plus `.ruff_cache`) returned **no maintainer-name matches** in tracked project content.
- Remaining GUID matches are limited to Azure built-in role definition IDs in `infra/modules/rbac.bicep`, `infra/modules/aci-identity.bicep`, and `infra/modules/aci-backend-role.bicep`; these are expected informational matches, not personal references.
- Re-run the full verification grep once the parallel infra/backend/frontend slices land, then append a final whole-repo clean result after their changes merge.
