## ADDED Requirements

### Requirement: Research Management UI
The web frontend SHALL provide a research management interface with search trigger, list, detail view, and delete capabilities.

#### Scenario: Research list view
- **WHEN** the user navigates to the Research page
- **THEN** a data table SHALL display all research entries with columns: title, mode (web search / deep research), linked idea, date
- **AND** each row SHALL be clickable to view the full result

#### Scenario: Trigger new research
- **WHEN** the user clicks "New Research"
- **THEN** a dialog SHALL appear with a query input, mode toggle (web search / deep research), and optional idea selector
- **AND** on submit, the research SHALL be triggered via the REST API

#### Scenario: Research detail view
- **WHEN** the user clicks on a research entry
- **THEN** the detail view SHALL render the result as formatted markdown with clickable citation links

#### Scenario: Deep research loading state
- **WHEN** deep research is in progress
- **THEN** the UI SHALL show a clear loading indicator explaining it may take several minutes

#### Scenario: Delete research
- **WHEN** the user clicks delete on a research entry
- **THEN** a confirmation dialog SHALL appear and on confirmation the entry SHALL be deleted

### Requirement: Idea-Research Integration
The idea detail view SHALL display linked research entries and allow triggering research from an idea.

#### Scenario: Show linked research on idea
- **WHEN** the user views an idea that has linked research
- **THEN** the detail view SHALL show a "Research" section listing all linked research entries

#### Scenario: Research from idea
- **WHEN** the user clicks "Research this idea" on an idea detail view
- **THEN** the research dialog SHALL open with the idea's title pre-filled as the query and the ideaId pre-linked
