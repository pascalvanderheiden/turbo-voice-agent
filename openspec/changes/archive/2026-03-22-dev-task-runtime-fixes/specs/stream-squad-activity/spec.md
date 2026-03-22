## ADDED Requirements

### Requirement: Parse squad agent activity from CLI stream
The system SHALL parse squad agent activity lines from the Copilot CLI SSE stream in real-time. Lines matching patterns like `Agent-name: Task description` or `● General-purpose(model) EmojiAgentName: Task description` SHALL be extracted to identify the agent name and their current task.

#### Scenario: Agent starts a task
- **WHEN** the stream emits a line containing "Trinity: Build sexy todo app UI"
- **THEN** the system SHALL update the squad member named "Trinity" (or closest match) with activity "Build sexy todo app UI" and status "working"

#### Scenario: Multiple agents working in parallel
- **WHEN** the stream emits activity for Trinity, Morpheus, and Scribe concurrently
- **THEN** each corresponding squad member SHALL be updated independently with their respective activity

### Requirement: Store activity on SquadMember
The SquadMember model SHALL include an `activity` field (string, default empty) that holds the current task description for that member.

#### Scenario: Activity field populated
- **WHEN** squad agent activity is parsed from the stream
- **THEN** the SquadMember's `activity` field SHALL contain the task description (e.g., "Build sexy todo app UI")

### Requirement: Real-time squad updates during pipeline
The system SHALL call `set_squad()` to persist squad member activity updates as they are detected in the stream, without waiting for the stage to complete.

#### Scenario: Live update during implement stage
- **WHEN** the implement stage is running and squad activity is detected
- **THEN** the squad member status and activity SHALL be updated in the service immediately, visible to polling clients
