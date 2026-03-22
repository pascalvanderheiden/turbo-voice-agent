## MODIFIED Requirements

### Requirement: Phase-based pipeline visualization
Replace the phase layout to match simplified pipelines. Mockup shows 4 stages inline: init→skills→implement→screenshots. Sequential shows: init→skills section, then implement-foundation row, then implement-feature-N rows, then screenshots (gated on all implements complete).

#### Scenario: Mockup task visualization
- **WHEN** a mockup dev task is displayed
- **THEN** the pipeline shows a single row with 4 stages: Init, Skills, Implement, Screenshots with running/completed/pending indicators

#### Scenario: Sequential foundation running
- **WHEN** a sequential task's implement-foundation stage is active
- **THEN** the visualization shows Init ✓, Skills ✓, Implement Foundation (running), with feature rows below in pending state

#### Scenario: Sequential foundation complete, features running
- **WHEN** implement-foundation is complete and feature implementations are in progress
- **THEN** Foundation shows a "✓ Foundation" completed badge, each feature shows its own implement row with status

#### Scenario: All features complete, screenshots eligible
- **WHEN** all implement-feature-N stages have status complete
- **THEN** Screenshots stage appears as active/next, visible below features section

#### Scenario: Foundation still running, features queued
- **WHEN** Foundation is not yet complete and feature stages exist
- **THEN** Feature rows show "Queued" state, screenshots not visible yet

### Requirement: Responsive stage labels
Stage labels shorten on narrow screens and wrap to continue underneath when they don't fit.

#### Scenario: Narrow viewport for mockup
- **WHEN** the mockup pipeline visualization renders on a narrow screen
- **THEN** Labels use abbreviated names (Init, Skills, Impl, Screens) and wrap to a second row if needed

#### Scenario: Narrow viewport for sequential
- **WHEN** the sequential pipeline visualization renders on a narrow screen
- **THEN** Foundation and feature implement labels truncate feature names and wrap as needed

### Requirement: Feature iteration progress tracking
Each feature iteration's implement stage status is tracked independently.

#### Scenario: Feature completes implementation
- **WHEN** a feature's implement-feature-N stage finishes
- **THEN** That feature row shows "✓ Complete" with green indicator, next feature or screenshots activates

### Requirement: Updated stage metadata
The frontend STAGE_META mapping SHALL reflect the new stage names. Remove entries for `openspec`, `propose`, `apply`, `archive`. Add entry for `implement` with appropriate icon and color.

#### Scenario: Stage metadata for implement
- **WHEN** an implement stage is rendered
- **THEN** it uses a code/build icon with brand cyan color

#### Scenario: No openspec stage in metadata
- **WHEN** the frontend renders any pipeline
- **THEN** there are no `openspec`, `propose`, `apply`, or `archive` entries in STAGE_META
