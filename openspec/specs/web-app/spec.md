## MODIFIED Requirements

### Requirement: Agent page Sandbox Config section
The system SHALL display a dedicated Sandbox Config section on the Agent page where users can configure the GitHub Copilot CLI sandbox settings.

#### Scenario: Sandbox Config section visible
- **WHEN** a user navigates to the Agent page
- **THEN** they SHALL see a "Sandbox Config" section containing: sandbox connection status, default model selector, and a link to manage GitHub authentication in profile settings

#### Scenario: Model selection
- **WHEN** a user selects a different model from the Sandbox Config dropdown
- **THEN** the selected model SHALL be persisted to the user's profile and used for subsequent dev task executions in the sandbox

#### Scenario: Sandbox status display
- **WHEN** the Sandbox Config section loads
- **THEN** it SHALL display the current sandbox status (running, stopped, recreating), skill sync status, and the configured GitHub auth status

### Requirement: Profile settings — GitHub sandbox auth
The system SHALL extend the profile settings page with a GitHub sandbox authentication section, following the same UI pattern as the existing To-Do connection.

#### Scenario: Auth section in profile settings
- **WHEN** a user navigates to profile settings
- **THEN** they SHALL see a "GitHub Copilot Sandbox" section with connect/disconnect controls and connection status, positioned alongside the existing To-Do connection

### Requirement: Dev task UI — Mockup and OpenSpec modes
The system SHALL update the dev task creation and detail views to support the new Mockup and OpenSpec modes.

#### Scenario: Create dev task with mode selection
- **WHEN** a user creates a dev task from a spec
- **THEN** the mode selector SHALL offer "Mockup" and "OpenSpec" options (replacing the previous "Mock" and "Sequence" options)

#### Scenario: Live CLI output viewer
- **WHEN** a dev task is executing
- **THEN** the dev task detail view SHALL display a real-time terminal-style viewer showing the GitHub Copilot CLI output streamed from the sandbox

#### Scenario: Screenshot gallery
- **WHEN** a dev task completes
- **THEN** the dev task detail view SHALL display a gallery of captured screenshots with thumbnail and full-size viewing

#### Scenario: Code download button
- **WHEN** a dev task completes successfully
- **THEN** the dev task detail view SHALL display a "Download Code" button that downloads the generated project as a zip archive

### Requirement: Add Feature UI on spec detail page
The web app SHALL provide an "Add Feature" action on the spec detail page that allows users to describe a new feature and submit it for AI enhancement and addition to the spec.

#### Scenario: Add Feature button visible on foundation specs
- **WHEN** a user views a foundation spec's detail page
- **THEN** an "Add Feature" button SHALL be visible
- **AND** clicking it SHALL open an input form with a text field for the feature description and a submit button

#### Scenario: Add Feature button hidden on feature specs
- **WHEN** a user views a feature-type spec's detail page
- **THEN** the "Add Feature" button SHALL NOT be visible

#### Scenario: Submit feature description
- **WHEN** a user enters a feature description and clicks submit
- **THEN** the UI SHALL call `add_feature_to_spec` via the API
- **AND** show a loading state with "Enhancing feature with AI..."
- **AND** on completion, refresh the spec content to show the appended feature

#### Scenario: Feature addition reflected in dev task view
- **WHEN** a feature is dynamically added to a spec with a linked dev task
- **THEN** the dev task detail view SHALL show the new feature iteration
- **AND** display its individual status (queued → running → completed)

### Requirement: Dynamic iteration display in dev task view
The web app SHALL display dynamically added feature iterations in the dev task detail view with per-feature status tracking.

#### Scenario: New iteration appears in real-time
- **WHEN** a feature iteration is appended to a dev task while the user is viewing it
- **THEN** the iteration list SHALL update to show the new feature
- **AND** the feature's pipeline progress (propose → apply → screenshots) SHALL be visible

#### Scenario: Queued iteration display
- **WHEN** a feature iteration has status "queued" (waiting for foundation)
- **THEN** the iteration SHALL display with a "Waiting for foundation" indicator
