## ADDED Requirements

### Requirement: Import OpenSpec project folder
The system SHALL accept a local OpenSpec project folder via the UI and create specs from its contents. The folder MUST contain at least a `specs/` directory with one or more `<name>/spec.md` files. The `project.md` and `changes/` directory are optional but enhance the import.

#### Scenario: Import folder with specs only
- **WHEN** user selects a folder containing `specs/notes-service/spec.md` and `specs/auth/spec.md`
- **THEN** the system SHALL create one foundation spec titled after the folder name
- **AND** create one feature spec per `specs/<name>/spec.md` file found, with content from each spec file
- **AND** each created spec SHALL have `formatVersion: "imported"`

#### Scenario: Import folder with project.md
- **WHEN** user selects a folder containing `project.md` and `specs/` directory
- **THEN** the system SHALL use `project.md` content as the foundation spec description
- **AND** include the project context in the foundation spec's content section

#### Scenario: Import folder with change history
- **WHEN** user selects a folder containing `changes/add-auth/proposal.md` and `changes/add-auth/design.md`
- **THEN** the system SHALL append a "Change History" section to the foundation spec
- **AND** each change SHALL show its name, proposal summary, and design decisions chronologically

#### Scenario: Import folder with no specs directory
- **WHEN** user selects a folder that does not contain a `specs/` directory
- **THEN** the system SHALL return an error: "No specs/ directory found in the selected folder"

### Requirement: OpenSpec folder parser
The system SHALL provide a parser utility that extracts structured data from an OpenSpec project folder. The parser SHALL handle the standard OpenSpec layout: `project.md`, `specs/<name>/spec.md`, and `changes/<name>/*.md`.

#### Scenario: Parse complete project
- **WHEN** the parser receives files from a folder with `project.md`, `specs/`, and `changes/`
- **THEN** it SHALL return a structured result containing: project context (string), list of capability specs (name + content), and list of changes (name + proposal + design + tasks)

#### Scenario: Parse spec file content
- **WHEN** the parser reads a `specs/<name>/spec.md` file
- **THEN** it SHALL extract the spec name from the directory path
- **AND** preserve the full markdown content including requirements and scenarios

### Requirement: Import UI on specs page
The system SHALL display an "Import OpenSpec" button on the Specs page that opens a folder picker dialog using `webkitdirectory`. The dialog SHALL show a preview of detected specs before confirming the import.

#### Scenario: Folder picker selection
- **WHEN** user clicks "Import OpenSpec" and selects a folder
- **THEN** the system SHALL display the folder name, number of detected specs, number of changes found, and whether `project.md` exists

#### Scenario: Confirm import
- **WHEN** user reviews the preview and clicks "Import"
- **THEN** the system SHALL upload all files via FormData to the backend import endpoint
- **AND** show a progress indicator during upload and processing
- **AND** navigate to the newly created foundation spec on completion

#### Scenario: Cancel import
- **WHEN** user reviews the preview and clicks "Cancel"
- **THEN** the system SHALL close the dialog without making any changes

### Requirement: Import origin indication
All specs created via import SHALL be visually distinguished from natively generated specs. The system SHALL display an "Imported" badge on imported specs in both the list view and detail view.

#### Scenario: Imported badge in list view
- **WHEN** the specs list page renders a spec with `formatVersion: "imported"`
- **THEN** it SHALL display an "Imported" badge next to the spec title

#### Scenario: Imported badge in detail view
- **WHEN** the spec detail page renders a spec with `formatVersion: "imported"`
- **THEN** it SHALL display an "Imported" badge below the header

#### Scenario: Filter by import origin
- **WHEN** specs are listed
- **THEN** imported specs SHALL be sorted alongside other specs by `updatedAt` (no separate grouping)
