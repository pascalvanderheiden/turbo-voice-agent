## Context

The app generates specs from ideas using GPT, but there's no reverse path — importing an existing OpenSpec project back into the spec system. OpenSpec projects follow a well-defined folder structure: `project.md` (project context), `specs/<name>/spec.md` (capability specs), and `changes/<name>/` (change history with proposal.md, design.md, tasks.md). The same `webkitdirectory` folder upload pattern used for skill uploads can be reused here.

Current spec creation flows: (1) manual creation via UI, (2) AI generation from idea, (3) add feature to existing spec. All store specs in Cosmos DB with `formatVersion: "v2"`. This change adds a fourth flow: folder import.

## Goals / Non-Goals

**Goals:**
- Parse a local OpenSpec project folder and create foundation + feature specs from its contents
- Synthesize change history (proposals, designs) into enriched spec content
- Tag imported specs with an "Imported" origin badge so users know the source
- Reuse the existing folder upload pattern (webkitdirectory → FormData → backend)
- Support both complete projects (with changes/) and minimal projects (just specs/)

**Non-Goals:**
- Two-way sync between local OpenSpec projects and the app (one-time import only)
- Importing non-OpenSpec project formats (e.g., plain markdown, Notion exports)
- Git history analysis (we parse file contents, not commit history)
- Auto-linking imported specs to existing ideas or dev tasks

## Decisions

### 1. Folder upload via FormData (same pattern as skill upload)
**Decision**: Reuse the `webkitdirectory` folder picker and FormData upload pattern from the skill upload feature.
**Rationale**: Already proven in production. Frontend sends files with `webkitRelativePath` preserved, backend reconstructs the folder tree. No new upload infrastructure needed.
**Alternative considered**: Zip file upload — adds complexity (zip parsing) with no UX benefit since the folder picker is cleaner.

### 2. Backend parser as a utility function (not a service class)
**Decision**: Create `app/utils/openspec_parser.py` with pure functions that parse the folder structure into a typed dict.
**Rationale**: Parsing is stateless and doesn't need Cosmos DB access. Keeping it as a utility makes it testable in isolation. The route handler orchestrates between parser output and SpecService calls.

### 3. One foundation spec per imported project, features from specs/ folder
**Decision**: The importer creates one foundation spec (from `project.md` context + synthesized change history) and one feature spec per `specs/<name>/spec.md` file found.
**Rationale**: Maps directly to the existing spec hierarchy (foundation → features). The `project.md` provides the overarching context that becomes the foundation, while individual capability specs become features.

### 4. Change history synthesis via string concatenation (no AI)
**Decision**: Concatenate change proposals and designs chronologically into a "Change History" section of the foundation spec content, rather than using AI to summarize.
**Rationale**: Preserves original author intent without hallucination risk. Users can see exactly what changes were proposed and why. AI summarization can be added later as an optional "optimize" step.

### 5. `formatVersion: "imported"` as origin tag
**Decision**: Extend the `formatVersion` field to support `"imported"` as a third value alongside `"v1"` and `"v2"`.
**Rationale**: Minimal model change, reuses an existing field, and clearly distinguishes imported specs in queries and UI. The frontend already reads `formatVersion` for rendering decisions.

## Risks / Trade-offs

- **[Large projects]** → A project with 50+ specs could create many Cosmos documents in one request. Mitigation: Process sequentially with progress logging; consider a batch limit with warning.
- **[Malformed OpenSpec folders]** → Missing `project.md` or unexpected structure. Mitigation: Parser validates structure upfront and returns clear errors for missing/malformed files.
- **[Duplicate imports]** → User imports the same project twice. Mitigation: Check for existing specs with matching titles; warn but allow (append " (imported)" suffix).
- **[File size]** → Large spec files or many changes. Mitigation: Cap individual file size at 1MB and total upload at 50MB. Specs beyond that are unusual.
