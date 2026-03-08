## Context
The Turbo Voice Agent already has Notes, Brainstorm, and Research agents. The Spec Agent follows the same supervisor→specialist pattern. Specs are generated from ideas (or manually) using GPT-5.2 to produce concise, development-ready output.

## Goals
- Convert ideas into structured development specs with one click or voice command
- Allow manual CRUD for specs independent of ideas
- Produce concise, clear specs optimized by GPT-5.2 (using `max_completion_tokens`)
- Link specs back to their source idea when applicable
- Split specs into **foundation** (one per project/idea) and **feature specs** (minimal set of focused features)

## Non-Goals
- No code generation from specs (future feature)
- No project management or sprint planning
- No multi-user collaboration on specs

## Decisions
- **Model**: GPT-5.2 via existing East US 2 endpoint (same as brainstorm refine)
- **Storage**: JSON file persistence (in-memory fallback) + Cosmos DB service for production
- **Spec structure**: Two types:
  - `foundation` — One spec covering architecture, tech stack, patterns, data model, core conventions
  - `feature` — Minimal focused specs, each covering a single feature built on the foundation
- **Spec model fields**: Title, content (markdown), type (foundation/feature), source idea link, status (draft/optimized), parentId (feature specs point to their foundation spec)
- **LLM prompt for foundation**: System prompt instructs GPT-5.2 to produce a concise foundation spec covering Overview, Architecture, Tech Stack, Data Model, and Core Patterns
- **LLM prompt for features**: System prompt instructs GPT-5.2 to identify the minimum set of features, producing one feature spec per feature with Overview, Requirements, Acceptance Criteria, and Technical Notes
- **Generation flow**: When generating from an idea, the LLM first produces the foundation spec, then identifies and produces the minimal feature specs

## Risks / Trade-offs
- GPT-5.2 requires `max_completion_tokens` (not `max_tokens`) — already handled in brainstorm agent
- Generating multiple specs (foundation + features) may take a few seconds — acceptable for single-shot generation
- Feature count minimization relies on LLM judgment — prompt engineering keeps it focused
