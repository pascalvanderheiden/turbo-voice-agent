## MODIFIED Requirements

### Requirement: Squad activity display in dev-task detail
The dev-task detail StatusPanel SHALL display the current activity for each working squad member, showing the agent name and their task description.

#### Scenario: Working member shows activity
- **WHEN** a squad member has status "working" and activity "Build sexy todo app UI"
- **THEN** the StatusPanel SHALL display the activity text below the member's role

#### Scenario: Idle member shows no activity
- **WHEN** a squad member has status "idle" and no activity
- **THEN** the StatusPanel SHALL display the member without an activity line

### Requirement: Premium request count on dev-task cards
The dev-task overview list SHALL display the premium request count on each dev-task card. The dev-task detail header SHALL also display the premium request count.

#### Scenario: Overview card shows premium count
- **WHEN** a dev-task has premiumRequests of 5
- **THEN** the overview card SHALL display "5 premium requests" (or a compact badge like "5 PR")

#### Scenario: Detail header shows premium count
- **WHEN** a user views a dev-task detail page with premiumRequests of 3
- **THEN** the header area SHALL display the premium request count

### Requirement: Total elapsed time on dev-task overview cards
The dev-task overview list SHALL display the total elapsed time for each dev-task. The time SHALL be calculated from the earliest stage startedAt to the latest stage completedAt (or current time if still running).

#### Scenario: Completed task shows elapsed time
- **WHEN** a dev-task has stages spanning from 10:00 to 10:15
- **THEN** the overview card SHALL display "15m" or similar compact duration

#### Scenario: Running task shows live elapsed time
- **WHEN** a dev-task is currently running with earliest startedAt 5 minutes ago
- **THEN** the overview card SHALL display the elapsed time from start until now
