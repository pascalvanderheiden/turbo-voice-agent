# Change: Add Spec Agent

## Why
Users need a way to convert refined ideas into concise, development-ready specifications. Currently ideas can be brainstormed and refined, but there is no structured path from idea to actionable spec. A dedicated Spec Agent bridges this gap by generating clear, well-structured specs optimized by GPT-5.2.

## What Changes
- New **spec-service** capability: CRUD for specs with LLM-powered generation from ideas
- Specs are structured into two types:
  - **Foundation spec**: Covers the foundational elements of the application (architecture, tech stack, patterns, data model)
  - **Feature specs**: Cover specific features built on top of the foundation. Always kept to a minimum number of focused features.
- New **Spec Agent** registered with the supervisor for voice and API access
- **Web app** updated with a Specs page (list, view, create, edit, delete) and "Convert to spec" button on ideas. The UI groups specs by type (foundation vs features).
- **Voice mode** updated to support spec creation and retrieval via voice commands
- Specs are persisted with JSON file storage (in-memory) and Cosmos DB support

## Impact
- Affected specs: `spec-service` (new), `agent-orchestration`, `realtime-voice`, `web-app`
- Affected code: backend agents, services, routes, models; frontend pages, API, i18n, sidebar
