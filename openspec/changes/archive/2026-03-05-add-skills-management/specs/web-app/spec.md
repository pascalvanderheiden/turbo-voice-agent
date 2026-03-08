## ADDED Requirements

### Requirement: Skills Management UI on Agents Page
The agents page SHALL provide full skills lifecycle management: browse marketplace, install, delete, add local skills, and search — all with real-time notification feedback.

#### Scenario: Delete installed skill
- **WHEN** the user clicks the delete button on an installed skill card
- **THEN** a confirmation dialog SHALL appear
- **AND** on confirmation, `DELETE /api/agents/skills/{name}` SHALL be called
- **AND** a toast notification SHALL show "Skill deleted" on success
- **AND** the skills list SHALL auto-refresh

#### Scenario: Install marketplace skill
- **WHEN** the user clicks "Install" on a marketplace skill card
- **THEN** `POST /api/agents/skills/install` SHALL be called with the skill's repo and name
- **AND** a toast notification SHALL show "Installing {name}..."
- **AND** upon completion, the skill SHALL appear in the installed list with a "Skill installed" toast

#### Scenario: Search marketplace via backend proxy
- **WHEN** the user types in the skills search input
- **THEN** after 300ms debounce, `GET /api/agents/skills/search?q=<query>` SHALL be called
- **AND** results SHALL replace the marketplace grid with matching skills from skills.sh

#### Scenario: Add local skill
- **WHEN** the user clicks "Add Local Skill"
- **THEN** a dialog SHALL appear with path input and skill name input
- **AND** on submit, `POST /api/agents/skills/install-local` SHALL be called
- **AND** a toast notification SHALL confirm successful installation

#### Scenario: Marketplace card links
- **WHEN** marketplace skill cards are displayed
- **THEN** each card SHALL link to the correct skills.sh URL: `https://skills.sh/<owner>/<repo>/<skill-name>`
- **AND** clicking SHALL open the link in a new tab

### Requirement: Dev Task Skill Selection in Creation Dialog
The development task creation dialog SHALL allow users to select which installed skills the Dev Agent should use during code generation.

#### Scenario: Show skill chips in create dialog
- **WHEN** the user opens the "New Development Task" dialog
- **THEN** a "Skills" section SHALL display installed skills as toggleable chips
- **AND** each chip shows the skill name and can be toggled on/off

#### Scenario: Auto-suggest skills when spec selected
- **WHEN** the user selects a spec in the create dialog
- **THEN** `GET /api/dev/suggest-skills?specId=<id>` SHALL be called
- **AND** the suggested skills SHALL be pre-toggled as selected

#### Scenario: Show selected skills on dev task detail
- **WHEN** a dev task with selected skills is viewed on the detail page
- **THEN** the selected skill names SHALL be displayed as badges in the task header

## MODIFIED Requirements

### Requirement: Development Page
The web application SHALL provide a Development page for managing development tasks with pipeline tracking. Tasks SHALL display their mode (Mock/Sequence), iteration progress, linked spec information, and selected skills. The detail page SHALL display iterations with their individual stage pipelines and plan output.

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
- **AND** selected skills SHALL be shown as badges in the header

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
- **THEN** a dialog SHALL appear with title input, spec selector dropdown, mode selector, and skill selection chips
- **AND** submitting SHALL create the task with selected skills and optionally trigger the pipeline

#### Scenario: Trigger pipeline from detail page
- **WHEN** the user clicks "Run Pipeline" on a pending task
- **THEN** the pipeline SHALL start and the page SHALL poll for stage updates
