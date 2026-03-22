## ADDED Requirements

### Requirement: Squad status polling during pipeline execution
After each apply sub-task in the pipeline, the backend runs `squad status --json` in the sandbox to get current member activity. Parsed results update each SquadMember's status field (idle/working/done) via `svc.set_squad()`.

#### Scenario: Squad member becomes active during apply
- **WHEN** The pipeline executes an apply sub-task and `squad status` reports a member is assigned work
- **THEN** That member's status changes to "working" and the SquadPanel dot turns green/animated

#### Scenario: Squad member completes their work
- **WHEN** `squad status` reports a member has no active assignments after previously being "working"
- **THEN** That member's status changes to "done" and the dot turns solid green

### Requirement: Use --agent squad flag for Copilot CLI
When a dev-task has squad enabled (squad metadata exists), all Copilot CLI `--yolo` prompts use `copilot --agent squad --yolo` to route work through squad-pr's agent system.

#### Scenario: Copilot CLI runs in squad-enabled task
- **WHEN** The pipeline calls `_sandbox_exec` with a prompt for a task that has squad config in `.squad/`
- **THEN** The command includes `--agent squad` parameter

#### Scenario: Squad not initialized
- **WHEN** The pipeline runs a prompt but no `.squad/config.json` exists
- **THEN** The command runs without `--agent squad` (standard mode)

### Requirement: Active squad members shown on overview cards
Dev-task overview cards display a compact squad member row showing only members with status "working", using small avatars/initials with role emoji.

#### Scenario: Dev-task has working squad members
- **WHEN** A dev-task card renders and squad.teamMembers includes members with status "working"
- **THEN** A row of working member names with role emoji appears below the pipeline visualization

#### Scenario: No squad or no active members
- **WHEN** A dev-task has no squad data or all members are idle
- **THEN** No squad row is shown on the card
