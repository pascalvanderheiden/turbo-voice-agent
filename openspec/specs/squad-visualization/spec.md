## ADDED Requirements

### Requirement: Squad panel in dev-task detail
The dev-task detail page SHALL display a "Squad" panel showing the team members assigned to the dev task. The panel SHALL appear after the pipeline stages section when squad data is available.

#### Scenario: Squad data available
- **WHEN** the dev task has squad metadata with team members
- **THEN** a "Squad" panel renders showing each agent's name, role, expertise, and current status

#### Scenario: No squad data
- **WHEN** the dev task has no squad metadata (e.g., legacy tasks)
- **THEN** the squad panel is not rendered

### Requirement: Agent roster display
Each team member in the squad panel SHALL be displayed as a card with: agent name (with emoji), role title, expertise tags, and a status indicator (idle/working/done).

#### Scenario: Agent is working
- **WHEN** an agent has status "working"
- **THEN** the agent card shows an animated indicator (e.g., pulsing dot or spinner) in brand cyan color

#### Scenario: Agent is idle
- **WHEN** an agent has status "idle"
- **THEN** the agent card shows a neutral gray indicator

#### Scenario: Agent is done
- **WHEN** an agent has status "done"
- **THEN** the agent card shows a green checkmark indicator

### Requirement: Stage metadata for new stages
The frontend `STAGE_META` constant SHALL include entries for the 3 new stages (openspec, skills, squad) with appropriate Tabler icons, labels, and brand colors.

#### Scenario: All 8 stages rendered
- **WHEN** a dev task with 8 stages is displayed
- **THEN** all stages show with distinct icons: init (gear), openspec (file-code), skills (puzzle), squad (users-group), propose (chatbot), apply (package), archive (archive), screenshots (photo)

### Requirement: Squad metadata on DevTask model
The DevTask model SHALL include an optional `squad` field containing `teamMembers` (array of objects with name, role, expertise, status fields). The frontend Spec type SHALL be extended accordingly.

#### Scenario: DevTask API returns squad data
- **WHEN** the API returns a dev task that went through the squad stage
- **THEN** the response includes a `squad` object with `teamMembers` array

#### Scenario: DevTask API returns without squad data
- **WHEN** the API returns a legacy dev task without squad setup
- **THEN** the `squad` field is null or absent

### Requirement: Squad activity in pipeline output
Squad-related activity (agent hiring, routing, doctor checks) SHALL appear in the pipeline output stream under the "squad" stage label, visible in the expandable stage output section.

#### Scenario: User expands squad stage output
- **WHEN** user clicks on the squad stage in the pipeline view
- **THEN** they see the output of squad init, each hire command, and squad doctor results

---

## MODIFIED Requirements (from dev-task-runtime-fixes)

### Requirement: Agent architecture page displays all agents
The agent architecture page SHALL display tiles for ALL registered agents including the slides agent. The slides agent tile SHALL use a presentation icon and appropriate branding color.

#### Scenario: Slides agent visible on page
- **WHEN** a user visits the agent architecture page
- **THEN** a "slides" agent tile SHALL be displayed alongside the existing 9 agents (voice, chat, supervisor, notes, brainstorm, research, spec, dev, skills)
