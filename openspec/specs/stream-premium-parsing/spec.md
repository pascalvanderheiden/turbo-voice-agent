## ADDED Requirements

### Requirement: Parse premium requests from CLI stream
The system SHALL parse the Copilot CLI summary output line `Total usage est: N Premium requests` from the SSE stream after each `_sandbox_exec` invocation. The parsed integer N SHALL be used as the premium request count for that invocation.

#### Scenario: Successful premium parsing
- **WHEN** a `_sandbox_exec` call completes and the stream output contains "Total usage est: 3 Premium requests"
- **THEN** the system SHALL call `add_premium_requests(task_id, 3)` with the parsed value

#### Scenario: No premium line in output (timeout/kill)
- **WHEN** a `_sandbox_exec` call completes but no "Total usage est" line is found in the output
- **THEN** the system SHALL fall back to adding 1 premium request per invocation

### Requirement: Remove static model multiplier
The system SHALL remove the `_get_premium_multiplier()` function and the `_PREMIUM_MULTIPLIERS` dict. Premium request counting SHALL be based solely on CLI stream output parsing.

#### Scenario: Static multiplier removed
- **WHEN** premium requests are tracked for any `_sandbox_exec` prompt invocation
- **THEN** the system SHALL NOT use model name to determine premium cost

### Requirement: Sum premium requests across sequential stages
For sequential mode dev-tasks, the system SHALL sum premium requests from each stage (foundation + each feature). The total `premiumRequests` on the DevTask SHALL reflect the cumulative sum.

#### Scenario: Sequential pipeline with 3 features
- **WHEN** a sequential pipeline runs foundation (2 premium) + feature-1 (1 premium) + feature-2 (3 premium)
- **THEN** the DevTask premiumRequests SHALL be at least 6 (plus any from init/screenshots stages)
