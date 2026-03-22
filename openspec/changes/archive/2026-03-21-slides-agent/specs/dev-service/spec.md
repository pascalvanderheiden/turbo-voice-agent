## MODIFIED Requirements

### Requirement: Dev-task mode selection
The system SHALL support three dev-task modes: "mockup" (single iteration), "openspec" (multi-iteration with foundation + features), and "slides" (3-stage deck generation). The pipeline routing SHALL select the appropriate pipeline based on the task's mode field.

#### Scenario: Route slides mode to slides pipeline
- **WHEN** a dev-task with mode "slides" starts execution
- **THEN** system calls _run_slides_pipeline() with the task's slides content and configuration

#### Scenario: Existing modes unchanged
- **WHEN** a dev-task with mode "mockup" or "openspec" starts execution
- **THEN** system routes to existing _run_mockup_pipeline() or _run_openspec_pipeline() respectively

### Requirement: Dev-task archived field
The system SHALL include an `archived` boolean field (default false) on the DevTask model. List queries SHALL accept an optional archived filter parameter.

#### Scenario: New tasks default to non-archived
- **WHEN** a new dev-task is created
- **THEN** archived field is set to false

#### Scenario: List with archived filter
- **WHEN** list endpoint receives archived=true parameter
- **THEN** only archived tasks are returned

### Requirement: Dev-task export artifacts
The system SHALL include an optional `artifacts` field on the DevTask model for storing export output URLs (PDF, code archive).

#### Scenario: Artifacts populated for slides tasks
- **WHEN** a slides dev-task completes export stage
- **THEN** artifacts field contains pdfUrl and codeUrl

#### Scenario: Artifacts empty for non-slides tasks
- **WHEN** a mockup or openspec dev-task is retrieved
- **THEN** artifacts field is null or empty
