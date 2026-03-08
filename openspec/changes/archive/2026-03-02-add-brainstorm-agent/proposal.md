# Change: Add Brainstorm Agent with Image Support

## Why
Users need a dedicated brainstorm agent that helps translate raw ideas into development-ready drafts using GPT-5.2. The agent should identify gaps, ask clarifying questions, and produce structured outputs. Additionally, both brainstorm ideas and notes should support image/camera uploads to provide visual context — accessible from the web app, mobile app, and voice mode.

## What Changes
- New **Brainstorm Agent** registered in the supervisor's agent team, powered by GPT-5.2 for idea refinement
- New **Brainstorm Service** with CRUD for ideas (same pattern as notes), plus a `refine` action that uses GPT-5.2 to analyze, question, and draft
- New **Brainstorm UI** pages (list, create/edit dialog with image upload, detail view showing refined draft)
- **Image upload endpoint** (`POST /api/upload`) returning a URL, used by both brainstorm and notes
- **MODIFIED Notes Service & UI** to accept optional image attachments
- **MODIFIED Voice session** to include brainstorm function tools (create_idea, refine_idea, list_ideas, etc.)
- **MODIFIED Supervisor** to route brainstorm functions to the new agent

## Impact
- Affected specs: `brainstorm-service` (new), `notes-service`, `agent-orchestration`, `realtime-voice`, `web-app`
- Affected code: backend agents, services, routes, models; frontend pages, components, voice hook; mobile screens
