## ADDED Requirements

### Requirement: Archive dev-task
The system SHALL allow users to archive a dev-task, setting its archived status to true. Archived tasks SHALL be hidden from the default list view.

#### Scenario: Archive a completed task
- **WHEN** user archives a dev-task with status "completed"
- **THEN** system sets archived=true on the task, task no longer appears in default list

#### Scenario: Archive a failed task
- **WHEN** user archives a dev-task with status "failed"
- **THEN** system sets archived=true on the task

### Requirement: Unarchive dev-task
The system SHALL allow users to unarchive a previously archived dev-task, restoring it to the active list.

#### Scenario: Unarchive task
- **WHEN** user unarchives a dev-task
- **THEN** system sets archived=false, task reappears in default list

### Requirement: Filter dev-tasks by archive status
The system SHALL support filtering the dev-task list by archive status. The default view SHALL show only non-archived (active) tasks.

#### Scenario: Default list shows active tasks
- **WHEN** user opens dev-task list without filter
- **THEN** system returns only tasks where archived=false

#### Scenario: View archived tasks
- **WHEN** user selects "Show archived" filter
- **THEN** system returns only tasks where archived=true

#### Scenario: View all tasks
- **WHEN** user selects "Show all" filter
- **THEN** system returns all tasks regardless of archive status

### Requirement: Archive action in UI
The system SHALL provide archive/unarchive controls in both the dev-task list (card action) and detail view.

#### Scenario: Archive from list card
- **WHEN** user clicks archive button on a dev-task card
- **THEN** task is archived and removed from the active list with animation

#### Scenario: Archive from detail view
- **WHEN** user clicks archive button in dev-task detail header
- **THEN** task is archived, user sees confirmation, can navigate back to list
