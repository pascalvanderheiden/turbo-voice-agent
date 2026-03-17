## MODIFIED Requirements

### Requirement: Development Pipeline Execution
The dev-service SHALL execute pipeline stages as background tasks. The service SHALL support both full pipeline execution (foundation + all features) and **incremental feature pipeline execution** (single feature added after foundation).

#### Scenario: Incremental feature pipeline execution
- **WHEN** a new feature iteration is appended to an OpenSpec dev task with a completed foundation
- **THEN** the sandbox SHALL execute only the new feature's `openspec-propose` + `openspec-apply` in the existing project workspace
- **AND** restart the dev server and capture Playwright screenshots
- **AND** the task status SHALL remain "running" during feature execution and update to "completed" only when all iterations (including the new one) are done

#### Scenario: Queued feature executes after foundation
- **WHEN** a feature iteration with status "queued" exists on a dev task
- **AND** the foundation iteration completes successfully
- **THEN** the pipeline SHALL automatically pick up the queued feature and execute its `openspec-propose` + `openspec-apply`

#### Scenario: Multiple queued features
- **WHEN** multiple feature iterations are queued while foundation is running
- **THEN** the pipeline SHALL execute all queued features in parallel (up to max 3 concurrent) after foundation completes

## ADDED Requirements

### Requirement: Dev task feature iteration extension
The dev-service SHALL support dynamically appending feature iterations to an in-progress OpenSpec dev task.

#### Scenario: Append feature iteration
- **WHEN** the spec agent calls the dev service to append a feature iteration
- **THEN** the dev service SHALL create a new iteration with the feature's `openspec-propose` instruction, status "queued" or "pending" (depending on foundation status), and link it to the dev task

#### Scenario: Append rejected for mockup mode
- **WHEN** a feature iteration append is requested for a Mockup mode dev task
- **THEN** the dev service SHALL reject the request with an error indicating only OpenSpec mode supports incremental features

#### Scenario: Foundation completion triggers queued features
- **WHEN** the foundation iteration completes on a dev task that has queued feature iterations
- **THEN** the dev service SHALL transition all queued iterations to "pending" and trigger pipeline execution for them
