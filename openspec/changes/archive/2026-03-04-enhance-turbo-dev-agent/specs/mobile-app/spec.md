## MODIFIED Requirements

### Requirement: Development Screen
The mobile application SHALL provide a Development screen accessible from the More menu for viewing development tasks with mode indicators and iteration progress, matching the web app's functionality.

#### Scenario: View development tasks
- **WHEN** the user navigates to Development from the More menu
- **THEN** the screen SHALL display all dev tasks as cards
- **AND** each card SHALL show title, status, and a 4-stage progress indicator

#### Scenario: Dev list shows mode
- **WHEN** a user views the development task list on mobile
- **THEN** each task SHALL display a mode badge ("Mock" or "Sequence")
- **AND** sequence tasks SHALL show iteration progress

#### Scenario: Dev detail shows iterations
- **WHEN** a user views a sequence mode task detail on mobile
- **THEN** iterations SHALL be displayed as collapsible sections
- **AND** each iteration SHALL show its label and stage pipeline with Ionicons

#### Scenario: Plan output display
- **WHEN** a user taps on a completed Plan stage
- **THEN** the plan output SHALL be displayed as formatted text below the stage

#### Scenario: View development task detail
- **WHEN** the user taps a dev task
- **THEN** the detail screen SHALL show pipeline stage progress, stage outputs, and screenshot artifacts

## ADDED Requirements

### Requirement: Spec Detail Development Action
The mobile spec detail screen SHALL provide a "Develop" action to create linked dev tasks.

#### Scenario: Create dev task from spec on mobile
- **WHEN** a user taps "Develop" on a spec detail screen
- **THEN** an action sheet SHALL appear to choose the pipeline mode (Mock or Sequence)
- **AND** upon selection, a dev task SHALL be created and the user navigated to the dev detail screen
