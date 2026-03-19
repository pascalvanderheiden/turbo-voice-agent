## 1. Backend: OpenSpec Parser Utility

- [ ] 1.1 Create `backend/app/utils/openspec_parser.py` with `parse_openspec_folder()` function that accepts a dict of `{relative_path: content}` and returns structured data: project context, list of specs (name + content), list of changes (name + proposal + design + tasks)
- [ ] 1.2 Handle missing `project.md` gracefully (return empty project context)
- [ ] 1.3 Handle missing `changes/` directory gracefully (return empty changes list)
- [ ] 1.4 Validate that `specs/` directory exists with at least one `spec.md` — return error if not

## 2. Backend: Import Endpoint

- [ ] 2.1 Add `POST /api/specs/import-openspec` route in `backend/app/routes/specs.py` that accepts FormData with multiple files (using `webkitRelativePath` paths)
- [ ] 2.2 Reconstruct folder structure from uploaded files, pass to `parse_openspec_folder()`
- [ ] 2.3 Create foundation spec from project context + synthesized change history, with `formatVersion: "imported"` and `type: "foundation"`
- [ ] 2.4 Create feature specs from each `specs/<name>/spec.md`, linked to foundation via `parentId`, with `formatVersion: "imported"`
- [ ] 2.5 Return created spec IDs and summary (foundation id, feature count, changes found)

## 3. Backend: Model Update

- [ ] 3.1 Update `backend/app/models/spec.py` to add `"imported"` as a valid `formatVersion` value in the Literal type
- [ ] 3.2 Verify Cosmos DB service handles `formatVersion: "imported"` without issues (no schema validation blocks)

## 4. Frontend: Import Dialog

- [ ] 4.1 Add "Import OpenSpec" button to the Specs page header (next to existing Create button)
- [ ] 4.2 Create import dialog with `webkitdirectory` folder picker (reuse pattern from skill upload)
- [ ] 4.3 After folder selection, show preview: folder name, detected spec count, changes count, project.md presence
- [ ] 4.4 On confirm, upload all files via FormData to `POST /api/specs/import-openspec`, show progress indicator
- [ ] 4.5 On success, navigate to the newly created foundation spec

## 5. Frontend: Import Badge

- [ ] 5.1 Add "Imported" badge rendering in the specs list page for specs with `formatVersion === "imported"` (use a distinct color, e.g., amber/orange)
- [ ] 5.2 Add "Imported" badge rendering in the spec detail page header
- [ ] 5.3 Add `specsApi.importOpenspec()` function in `frontend/src/lib/api.ts` that sends FormData to the import endpoint

## 6. Testing & Verification

- [ ] 6.1 Test import with a complete OpenSpec project folder (project.md + specs/ + changes/)
- [ ] 6.2 Test import with minimal folder (specs/ only, no project.md or changes/)
- [ ] 6.3 Test import with empty or invalid folder (no specs/ directory) — verify error message
- [ ] 6.4 Verify imported specs display correctly in list and detail views with badge
