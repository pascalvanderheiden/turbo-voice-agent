## Why

Building apps with Turbo Agent generates rich OpenSpec artifacts (proposals, designs, specs, tasks) in the sandbox, but there's no way to reverse-engineer an existing OpenSpec project back into the app's spec system. Developers who already have local OpenSpec projects — or who want to import specs from other repos — currently have to manually recreate everything. Importing a folder would let users bootstrap their spec library instantly and see the full history of changes that shaped each capability.

## What Changes

- **New folder import UI**: Add an "Import OpenSpec" button to the Specs page that opens a folder picker (webkitdirectory). User selects a local OpenSpec project folder containing `project.md`, `specs/`, and `changes/`.
- **Backend import endpoint**: New `POST /api/specs/import-openspec` endpoint that receives the folder contents, parses OpenSpec structure, and creates foundation + feature specs in Cosmos DB.
- **Change history synthesis**: The importer reads all `changes/*/proposal.md`, `design.md`, and `tasks.md` to reconstruct how the project evolved, incorporating change context into the generated spec content.
- **Import origin badge**: Specs created via import are tagged with `formatVersion: "imported"` and display an "Imported" badge in the UI, distinguishing them from specs generated natively.
- **OpenSpec parser utility**: Backend utility that understands the OpenSpec folder structure (`project.md`, `specs/<name>/spec.md`, `changes/<name>/*.md`) and extracts structured data.

## Capabilities

### New Capabilities
- `openspec-import`: Folder-based import of a local OpenSpec project into the app's spec system, including change history synthesis, origin tagging, and UI for selecting and reviewing imports.

### Modified Capabilities
- `spec-service`: Add `formatVersion: "imported"` support, import origin metadata, and "Imported" badge rendering in the spec list and detail views.

## Impact

- **Backend**: New route in `specs.py`, new parser utility in `app/services/` or `app/agents/`, updated spec model to support `"imported"` format version.
- **Frontend**: New import button + folder picker dialog on specs page, "Imported" badge in spec list/detail, potentially a preview step before confirming import.
- **Spec model**: `formatVersion` enum gains `"imported"` value. No breaking changes — existing specs unaffected.
- **Dependencies**: No new external dependencies. Uses existing `webkitdirectory` folder upload pattern (same as skill upload).
