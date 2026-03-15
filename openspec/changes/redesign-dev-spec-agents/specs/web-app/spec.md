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
