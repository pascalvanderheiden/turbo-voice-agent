## MODIFIED Requirements

### Requirement: Spec Naming
The spec-service SHALL store spec titles without type suffixes. When returning specs via the API, the title field SHALL contain only the user-provided title (e.g., "My App") without appending "- Foundation" or "- Feature". The spec type SHALL be conveyed solely through the `type` field in the spec data model. Existing specs with type suffixes in titles SHALL be normalized on read.

#### Scenario: Create a foundation spec
- **WHEN** a foundation spec is created with title "My App"
- **THEN** the stored title SHALL be "My App" (not "My App - Foundation")
- **AND** the `type` field SHALL be "foundation"

#### Scenario: Create a feature spec
- **WHEN** a feature spec is created with title "Dark Theme"
- **THEN** the stored title SHALL be "Dark Theme" (not "Dark Theme - Feature")
- **AND** the `type` field SHALL be "feature"

#### Scenario: List specs returns clean titles
- **WHEN** specs are listed via `GET /api/specs`
- **THEN** all titles SHALL be returned without type suffixes
- **AND** foundation specs SHALL be ordered before feature specs
