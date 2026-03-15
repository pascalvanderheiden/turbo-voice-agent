## MODIFIED Requirements

### Requirement: Spec CRUD
The system SHALL provide full CRUD operations for development specs, including create, read, update, delete, list, and **add feature**. Each spec SHALL have a type field of either "foundation" or "feature".

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

## ADDED Requirements

### Requirement: Spec feature tool definition
The spec agent SHALL expose an `add_feature_to_spec` tool to the supervisor for routing via voice and API.

#### Scenario: Tool definition schema
- **WHEN** the supervisor queries the spec agent's tool definitions
- **THEN** the tool list SHALL include `add_feature_to_spec` with parameters: `spec_id` (string, required) and `description` (string, required — the feature description to enhance and add)

#### Scenario: Tool execution
- **WHEN** the supervisor routes an `add_feature_to_spec` call to the spec agent
- **THEN** the spec agent SHALL execute the enhancement pipeline as a background task
- **AND** return a status message indicating the feature enhancement has started
