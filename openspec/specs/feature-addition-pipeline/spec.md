### Requirement: Add feature to spec pipeline
The system SHALL provide an `add_feature_to_spec` function that accepts a spec ID and a feature description, enhances the description using GPT-5.2, appends the enhanced feature to the spec, and — if a linked OpenSpec dev task exists with a completed foundation — automatically extends the dev task and triggers incremental pipeline execution.

#### Scenario: Add feature via voice
- **WHEN** a user says "add dark mode to my spec" during a voice session
- **THEN** the voice agent SHALL resolve the spec (via `get_specs` or context), call `add_feature_to_spec(spec_id, "dark mode support")`, and confirm the feature was added and enhanced

#### Scenario: Add feature via UI
- **WHEN** a user clicks "Add Feature" on the spec detail page and submits a description
- **THEN** the system SHALL call the same `add_feature_to_spec` endpoint and display the enhanced feature in the spec view

#### Scenario: GPT-5.2 enhancement
- **WHEN** `add_feature_to_spec` is called with a raw description
- **THEN** the system SHALL send the description along with the existing spec content to GPT-5.2
- **AND** GPT-5.2 SHALL produce: (1) a Mockup Description paragraph for the feature, and (2) an `openspec-propose` instruction for the feature
- **AND** both artifacts SHALL be appended to the respective sections of the spec

#### Scenario: Auto-extend dev task when foundation complete
- **WHEN** a feature is added to a spec that has a linked OpenSpec dev task
- **AND** the dev task's foundation iteration has status "completed"
- **THEN** the system SHALL append a new feature iteration to the dev task
- **AND** trigger the dev pipeline for that feature iteration only

#### Scenario: Queue feature when foundation in progress
- **WHEN** a feature is added to a spec that has a linked OpenSpec dev task
- **AND** the dev task's foundation iteration has status "running" or "pending"
- **THEN** the system SHALL append a new feature iteration with status "queued"
- **AND** the pipeline SHALL execute the queued feature after foundation completes

#### Scenario: No linked dev task
- **WHEN** a feature is added to a spec that has no linked dev task
- **THEN** the system SHALL only update the spec content
- **AND** SHALL NOT create a dev task or trigger any pipeline

#### Scenario: Feature status lifecycle
- **WHEN** a feature is added via `add_feature_to_spec`
- **THEN** the feature SHALL progress through statuses: `enhancing` (GPT-5.2 processing) → `enhanced` (appended to spec) → `dev-queued` (if dev task exists, waiting for foundation) → `dev-running` (pipeline executing) → `dev-completed` (pipeline finished)

### Requirement: Feature enhancement quality
The GPT-5.2 enhancement SHALL produce feature content consistent with the existing spec's two-part format and quality level.

#### Scenario: Enhancement includes existing spec context
- **WHEN** GPT-5.2 enhances a feature description
- **THEN** the system SHALL include the full existing spec content as context in the prompt
- **AND** the enhanced feature SHALL be coherent with the existing foundation and features

#### Scenario: Enhancement follows two-part format
- **WHEN** GPT-5.2 produces the enhanced feature
- **THEN** the Mockup Description paragraph SHALL describe visual/interaction aspects in ~50-100 words
- **AND** the OpenSpec Config instruction SHALL be a clear, self-contained `openspec-propose` prompt

#### Scenario: Background task execution
- **WHEN** `add_feature_to_spec` is called
- **THEN** the operation SHALL run as a background task (similar to `generate_spec`)
- **AND** the voice session SHALL notify the user upon completion
