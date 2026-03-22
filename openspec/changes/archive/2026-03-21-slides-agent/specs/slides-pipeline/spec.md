## ADDED Requirements

### Requirement: Slides dev-task pipeline mode
The system SHALL support a "slides" mode for dev-tasks that executes a 3-stage pipeline: init, slides, export. This mode SHALL be selectable when creating a dev-task from a slide presentation.

#### Scenario: Create slides dev-task
- **WHEN** user triggers "Develop" on a refined slide presentation
- **THEN** system creates a dev-task with mode "slides" and stages: init, slides, export

#### Scenario: Pipeline stage ordering
- **WHEN** a slides dev-task starts executing
- **THEN** stages execute in order: init → slides → export, each completing before the next begins

### Requirement: Init stage clones deck-engine
The init stage SHALL create a fresh workspace, initialize git, and clone the deck-engine repository (https://github.com/deckio-art/deck-engine) into the sandbox.

#### Scenario: Successful init
- **WHEN** init stage executes
- **THEN** sandbox workspace is created, git initialized, deck-engine cloned, and dependencies installed

#### Scenario: Init failure on clone
- **WHEN** deck-engine repository is unreachable during clone
- **THEN** init stage fails with error message, pipeline stops, task status set to "failed"

### Requirement: Slides stage generates deck via Copilot CLI
The slides stage SHALL use GitHub Copilot CLI in the sandbox to generate slide content based on the presentation's refined description, sections, and file context. The prompt SHALL include the structured sections and any extracted file content.

#### Scenario: Generate slides from refined description
- **WHEN** slides stage executes with a refined presentation containing 5 sections
- **THEN** Copilot CLI generates deck-engine slide files for each section using the structured content

#### Scenario: Stream output during generation
- **WHEN** slides stage is executing
- **THEN** sandbox streams CLI output to the frontend terminal view in real-time

### Requirement: Export stage renders PDF
The export stage SHALL start the deck-engine dev server, use a headless browser to capture each slide page, combine them into a single PDF, and upload to blob storage.

#### Scenario: Successful PDF export
- **WHEN** export stage executes after slides are generated
- **THEN** system starts deck-engine server, captures each slide as a PDF page, combines into single PDF, uploads to blob storage at slides/{task_id}/export.pdf

#### Scenario: PDF preview available after export
- **WHEN** export stage completes successfully
- **THEN** dev-task detail view shows the PDF preview with page navigation

#### Scenario: Export failure
- **WHEN** headless browser fails to capture slides
- **THEN** export stage fails with error, task marked as failed, partial output preserved in stream

### Requirement: Pipeline progress reporting
The system SHALL report progress for each stage in the dev-task, updating the stage pipeline visualization.

#### Scenario: Stage transitions visible
- **WHEN** pipeline moves from init to slides stage
- **THEN** init stage shows as completed (green), slides stage shows as active (pulsing), export shows as pending

#### Scenario: Export progress per slide
- **WHEN** export stage is capturing slides
- **THEN** stream output shows progress per slide (e.g., "Exporting slide 3/10")
