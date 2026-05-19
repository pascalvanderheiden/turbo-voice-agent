# McManus — History

## Project Context
Turbo Voice Agent — web frontend for real-time voice agent.
Stack: Next.js 15 (App Router), React 19, TypeScript, shadcn/ui (new-york), Tailwind CSS v4, Tabler Icons.
User: the project maintainer.

Frontend features: voice mode UI, notes, dashboard, dev-task pipeline viewer, slides preview, SSE streaming for real-time updates. Auth via MSAL (Azure Entra ID).

## Learnings
- Slides pipeline stages changed: `init → skills → slides` is now `init → slides → run`. The `run` stage represents the Slidev dev server startup + health check.
- Auto-preview pattern: When `run` stage completes, `liveUrl` is auto-set to `/api/dev/{task_id}/preview/` — no user click needed. Uses a `useEffect` watching `task` state changes during polling.
- `STAGE_META` is duplicated in both `development/page.tsx` (list view) and `development/[id]/page.tsx` (detail view). Both need updating when stages change.
- The "Start Preview" button is kept as fallback for older tasks that may not have a `run` stage. It's disabled until `run` stage completes.
- `IconRocket` from Tabler is used for the `run` stage icon, green color (#22C55E) to match the "completion" aesthetic.
- Refresh button pattern: null out `liveUrl` then re-set after 100ms timeout to force iframe reload.
- OSS README rewrite now follows a deployment-first structure: hero, screenshot placeholder, key features, architecture, prerequisites, manual deploy, automated deploy, local dev, testing, contributing, license, acknowledgments.
- Governance templates chosen for OSS prep: MIT license, Contributor Covenant 2.1, and a GitHub Security Advisories-based security policy with response expectations.
- Frontend env examples now use a dedicated `.env.local.example` file with commented generic placeholders so README setup matches the actual local workflow.
