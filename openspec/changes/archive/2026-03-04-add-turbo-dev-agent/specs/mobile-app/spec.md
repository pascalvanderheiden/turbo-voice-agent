## ADDED Requirements

### Requirement: Development Screen
The mobile application SHALL provide a Development screen accessible from the More menu for viewing development tasks.

#### Scenario: View development tasks
- **WHEN** the user navigates to Development from the More menu
- **THEN** the screen SHALL display all dev tasks as cards
- **AND** each card SHALL show title, status, and a 4-stage progress indicator

#### Scenario: View development task detail
- **WHEN** the user taps a dev task
- **THEN** the detail screen SHALL show pipeline stage progress, stage outputs, and screenshot artifacts
