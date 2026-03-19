## MODIFIED Requirements

### Requirement: Spec generation output format
The system SHALL generate specs in a two-part format: (1) **Mockup Description** — a concise description of the frontend design demonstrating key features (~200 words, covering layout, components, interactions, and visual style), and (2) **OpenSpec Config** — a series of focused prompt instructions, starting with one `openspec-propose` instruction for the foundation and one `openspec-propose` instruction per feature.

#### Scenario: Generate spec from idea
- **WHEN** a user requests spec generation from an idea (via voice or UI)
- **THEN** the system SHALL produce a spec with exactly two sections: a `## Mockup Description` section containing a concise frontend design brief, and a `## OpenSpec Config` section containing structured `openspec-propose` prompt instructions

#### Scenario: Mockup Description content
- **WHEN** a spec is generated
- **THEN** the Mockup Description SHALL include: app name, layout structure, key UI components, primary user interactions, color scheme/visual identity, and a list of demonstrated features — all in ~200 words maximum

#### Scenario: OpenSpec Config content
- **WHEN** a spec is generated
- **THEN** the OpenSpec Config SHALL contain a `### Foundation` subsection with a single `openspec-propose` prompt instruction covering the app's core architecture, and a `### Features` subsection with one `openspec-propose` prompt instruction per feature, each focused and self-contained

#### Scenario: OpenSpec Config prompt quality
- **WHEN** the OpenSpec Config is consumed by the Copilot CLI
- **THEN** each `openspec-propose` instruction SHALL be a clear, focused prompt that can be directly used as input to the `openspec-propose` CLI command without further editing

### Requirement: Spec optimization
The system SHALL optimize specs while preserving the two-part format structure.

#### Scenario: Optimize preserves format
- **WHEN** a user requests spec optimization
- **THEN** the optimized spec SHALL retain both the Mockup Description and OpenSpec Config sections, refining content for clarity and conciseness within each section

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

### Requirement: Spec feature tool definition
The spec agent SHALL expose an `add_feature_to_spec` tool to the supervisor for routing via voice and API.

#### Scenario: Tool definition schema
- **WHEN** the supervisor queries the spec agent's tool definitions
- **THEN** the tool list SHALL include `add_feature_to_spec` with parameters: `spec_id` (string, required) and `description` (string, required — the feature description to enhance and add)

#### Scenario: Tool execution
- **WHEN** the supervisor routes an `add_feature_to_spec` call to the spec agent
- **THEN** the spec agent SHALL execute the enhancement pipeline as a background task
- **AND** return a status message indicating the feature enhancement has started

---

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
