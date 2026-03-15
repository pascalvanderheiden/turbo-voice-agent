## ADDED Requirements

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
