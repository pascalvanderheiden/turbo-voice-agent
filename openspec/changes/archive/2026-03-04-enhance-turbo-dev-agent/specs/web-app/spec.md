## ADDED Requirements

### Requirement: Skills Marketplace on Agents Page
The web app SHALL display a Skills Marketplace section on the Agents page, allowing users to browse available skills from skills.sh and view installed skills.

#### Scenario: Browse skills catalog
- **WHEN** a user navigates to the Agents page
- **THEN** a "Skills Marketplace" section SHALL be visible below the agent architecture diagram
- **AND** the section SHALL display skills from skills.sh as a searchable card grid
- **AND** each skill card SHALL show name, author/repo, description, and install count

#### Scenario: Search skills
- **WHEN** a user types in the skills search input
- **THEN** the displayed skills SHALL be filtered by name and description matching the search term

#### Scenario: View installed skills
- **WHEN** installed skills exist in the project's `.agents/skills/` directory
- **THEN** they SHALL be displayed in a separate "Installed Skills" section above the marketplace
- **AND** each installed skill SHALL show its name and description

## MODIFIED Requirements

### Requirement: Development Page
The web application SHALL provide a Development page for managing development tasks with pipeline tracking. Tasks SHALL display their mode (Mock/Sequence), iteration progress, and linked spec information. The detail page SHALL display iterations with their individual stage pipelines and plan output.

#### Scenario: View development task list
- **WHEN** the user navigates to /development
- **THEN** the page SHALL display all dev tasks in a card grid
- **AND** each card SHALL show the task title, linked spec name, overall status, and a 4-stage progress indicator (Plan, Build, Run, Test)
- **AND** status badges SHALL use yellow for pending, blue for running, green for completed, red for failed

#### Scenario: Show task mode
- **WHEN** a user views the development task list
- **THEN** each task SHALL display a badge indicating its mode ("Mock" or "Sequence")

#### Scenario: Show iteration progress in sequence mode
- **WHEN** a sequence mode task is displayed
- **THEN** the task SHALL show iteration progress (e.g., "2/5 iterations completed")
- **AND** the current iteration label SHALL be visible

#### Scenario: View development task detail
- **WHEN** the user clicks on a dev task
- **THEN** the detail page SHALL show a pipeline visualization with all 4 stages
- **AND** each stage SHALL show its status, output/logs, and duration
- **AND** screenshot artifacts SHALL be displayed as images
- **AND** a download button SHALL be available for the code archive when the task is completed

#### Scenario: View iterations
- **WHEN** a user views a sequence mode task detail
- **THEN** iterations SHALL be displayed as a vertical timeline with tabs or sections
- **AND** each iteration SHALL show its label (foundation/feature name) and stage pipeline

#### Scenario: View plan output
- **WHEN** a user expands a Plan stage in any iteration
- **THEN** the plan output SHALL be rendered as formatted markdown content
- **AND** the plan SHALL clearly reference which spec part (foundation or feature) it covers

#### Scenario: Create development task manually
- **WHEN** the user clicks "New Development Task"
- **THEN** a dialog SHALL appear with title input and spec selector dropdown
- **AND** submitting SHALL create the task and optionally trigger the pipeline

#### Scenario: Trigger pipeline from detail page
- **WHEN** the user clicks "Run Pipeline" on a pending task
- **THEN** the pipeline SHALL start and the page SHALL poll for stage updates

## ADDED Requirements

### Requirement: Spec Detail Page Development Action
The spec detail page SHALL provide a "Develop" action button that creates a linked dev task.

#### Scenario: Create dev task from spec
- **WHEN** a user clicks "Develop" on a spec detail page
- **THEN** a dialog SHALL appear allowing the user to choose the pipeline mode (Mock or Sequence)
- **AND** upon confirmation, a dev task SHALL be created linked to the spec
- **AND** the spec card SHALL show a "In Development" badge with a link to the dev task

#### Scenario: View linked dev task
- **WHEN** a spec has a linked dev task
- **THEN** the spec card on the list page SHALL show a development status indicator
- **AND** clicking the indicator SHALL navigate to the linked dev task detail page
