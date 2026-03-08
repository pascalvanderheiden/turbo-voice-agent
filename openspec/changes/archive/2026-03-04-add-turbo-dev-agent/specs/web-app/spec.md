## ADDED Requirements

### Requirement: Development Page
The web application SHALL provide a Development page for managing development tasks with pipeline tracking.

#### Scenario: View development task list
- **WHEN** the user navigates to /development
- **THEN** the page SHALL display all dev tasks in a card grid
- **AND** each card SHALL show the task title, linked spec name, overall status, and a 4-stage progress indicator (Plan, Build, Run, Test)
- **AND** status badges SHALL use yellow for pending, blue for running, green for completed, red for failed

#### Scenario: View development task detail
- **WHEN** the user clicks on a dev task
- **THEN** the detail page SHALL show a pipeline visualization with all 4 stages
- **AND** each stage SHALL show its status, output/logs, and duration
- **AND** screenshot artifacts SHALL be displayed as images
- **AND** a download button SHALL be available for the code archive when the task is completed

#### Scenario: Create development task manually
- **WHEN** the user clicks "New Development Task"
- **THEN** a dialog SHALL appear with title input and spec selector dropdown
- **AND** submitting SHALL create the task and optionally trigger the pipeline

#### Scenario: Trigger pipeline from detail page
- **WHEN** the user clicks "Run Pipeline" on a pending task
- **THEN** the pipeline SHALL start and the page SHALL poll for stage updates

## MODIFIED Requirements

### Requirement: Web Application Shell
The sidebar SHALL include navigation items for Dashboard, Notes, Ideas, Research, Specs, Development, Voice, and Agents. The Specs item SHALL use a file-code icon. The Development item SHALL use a Code icon and be positioned after Specs and before Agents.

#### Scenario: Specs nav item visible
- **WHEN** the sidebar is rendered
- **THEN** a "Specs" navigation item is visible between Research and Development

#### Scenario: Navigate to development
- **WHEN** the user clicks Development in the sidebar
- **THEN** the application SHALL navigate to /development
