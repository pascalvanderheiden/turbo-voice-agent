## ADDED Requirements

### Requirement: Phase-based pipeline visualization
Replace the single flat stage row with distinct phases: Foundation (all 7 stages), Features (compact propose→apply per iteration), and Screenshots (final, gated on all features complete).

#### Scenario: Foundation phase running
- **WHEN** Iteration 0 is active and not all stages are complete
- **THEN** The Foundation row shows full init→openspec→skills→squad→propose→apply→archive pipeline with running/completed/pending indicators

#### Scenario: Foundation complete, features running
- **WHEN** All iteration 0 stages are complete and feature iterations exist
- **THEN** Foundation shows a single "✓ Foundation" completed badge, each feature iteration shows its own compact propose→apply row with status

#### Scenario: All features complete, screenshots eligible
- **WHEN** All feature iterations have status complete
- **THEN** Screenshots stage appears as active/next, visible below features section

#### Scenario: Foundation still running, features queued
- **WHEN** Foundation is not yet complete and feature iterations exist
- **THEN** Feature rows show "Queued" state, screenshots not visible yet

### Requirement: Responsive stage labels
Stage labels shorten on narrow screens and wrap to continue underneath when they don't fit.

#### Scenario: Narrow viewport
- **WHEN** The pipeline visualization renders on a screen narrower than the stage row
- **THEN** Labels use abbreviated names (Init, Spec, Skills, Squad, Prop, Apply, Arch) and wrap to a second row if needed

### Requirement: Feature iteration progress tracking
Each feature iteration's pipeline status is tracked independently. When a feature's propose→apply completes, it's marked done before the next starts.

#### Scenario: Feature completes propose and apply
- **WHEN** A feature iteration finishes both propose and apply stages
- **THEN** That feature row shows "✓ Complete" with green indicator, next feature or screenshots activates

---

## MODIFIED Requirements (from dev-task-runtime-fixes)

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
