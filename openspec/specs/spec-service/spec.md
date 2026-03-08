# spec-service Specification

## Purpose
TBD - created by archiving change add-spec-agent. Update Purpose after archive.
## Requirements
### Requirement: Spec CRUD
The system SHALL provide full CRUD operations for development specs, including create, read, update, delete, and list. Each spec SHALL have a type field of either "foundation" or "feature".

#### Scenario: Create foundation spec manually
- **WHEN** a user creates a spec with type "foundation", a title and content
- **THEN** the system stores the spec with status "draft" and returns it with a unique ID

#### Scenario: Create feature spec manually
- **WHEN** a user creates a spec with type "feature", a title, content, and parentId referencing a foundation spec
- **THEN** the system stores the feature spec linked to the foundation spec

#### Scenario: Generate specs from idea
- **WHEN** a user requests spec generation for an existing idea
- **THEN** the system uses GPT-5.2 to first produce a foundation spec (Overview, Architecture, Tech Stack, Data Model, Core Patterns)
- **AND** then identifies the minimum set of features and produces one feature spec per feature (Overview, Requirements, Acceptance Criteria, Technical Notes)
- **AND** all specs are linked to the source idea via ideaId and feature specs reference the foundation spec via parentId

#### Scenario: List specs
- **WHEN** a user requests the spec list
- **THEN** the system returns all specs ordered by type (foundation first) then updatedAt descending

#### Scenario: Delete spec
- **WHEN** a user deletes a spec by ID
- **THEN** the spec is removed from storage

### Requirement: Spec Persistence
The system SHALL persist specs to JSON files for local development and to Cosmos DB when available.

#### Scenario: Data survives restart
- **WHEN** the backend restarts
- **THEN** previously created specs are loaded from disk and available via API

### Requirement: Spec LLM Optimization
The system SHALL use GPT-5.2 with max_completion_tokens to generate and optimize specs. The output SHALL be concise, clear, and structured in markdown. Feature count SHALL be kept to a minimum.

#### Scenario: Optimize existing spec
- **WHEN** a user triggers optimization on a draft spec
- **THEN** the system sends the spec content to GPT-5.2 for refinement
- **AND** updates the spec status to "optimized" and stores the improved content

