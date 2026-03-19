## MODIFIED Requirements

### Requirement: Spec CRUD
The system SHALL provide full CRUD operations for development specs, including create, read, update, delete, list, and **add feature**. Each spec SHALL have a type field of either "foundation" or "feature". The `formatVersion` field SHALL support values `"v1"`, `"v2"`, and `"imported"`.

#### Scenario: Create spec with imported format version
- **WHEN** a spec is created with `formatVersion: "imported"`
- **THEN** the system SHALL store the spec with the imported tag
- **AND** the spec SHALL be queryable and editable like any other spec

#### Scenario: Add feature to existing spec
- **WHEN** a user calls `add_feature_to_spec` with a valid spec ID and a feature description
- **THEN** the system SHALL enhance the description using GPT-5.2
- **AND** append the enhanced Mockup Description paragraph to the spec's `## Mockup Description` section
- **AND** append the enhanced `openspec-propose` instruction to the spec's `## OpenSpec Config` → `### Features` subsection
- **AND** update the spec's `updatedAt` timestamp

#### Scenario: Add feature to non-existent spec
- **WHEN** a user calls `add_feature_to_spec` with an invalid spec ID
- **THEN** the system SHALL return an error indicating the spec was not found

#### Scenario: Add feature to feature-type spec
- **WHEN** a user calls `add_feature_to_spec` on a spec with type "feature" (not "foundation")
- **THEN** the system SHALL return an error indicating features can only be added to foundation specs

#### Scenario: List specs includes imported
- **WHEN** the spec list is retrieved
- **THEN** specs with `formatVersion: "imported"` SHALL appear in the list with all standard fields
- **AND** be sortable and filterable like any other spec
