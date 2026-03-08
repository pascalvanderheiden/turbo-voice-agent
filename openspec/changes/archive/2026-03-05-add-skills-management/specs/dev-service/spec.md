## ADDED Requirements

### Requirement: Skills Management Service
The system SHALL provide a SkillsService that manages the lifecycle of agent skills — installing, uninstalling, listing, searching, and reading skill content for prompt injection.

#### Scenario: List installed skills with metadata
- **WHEN** `GET /api/agents/skills` is called
- **THEN** the system SHALL scan `.agents/skills/` and return each skill's name, description (from SKILL.md frontmatter), version, file count, and source ("local")

#### Scenario: Install skill from skills.sh marketplace
- **WHEN** `POST /api/agents/skills/install` is called with `{repo, skillName}`
- **THEN** the system SHALL execute `npx skills add <repo> --skill <skillName> -y` as a background subprocess
- **AND** return immediately with `{status: "installing", name: <skillName>}`
- **AND** upon completion, the skill SHALL appear in the installed skills list

#### Scenario: Install skill from local path
- **WHEN** `POST /api/agents/skills/install-local` is called with `{sourcePath, name}`
- **THEN** the system SHALL copy the directory at sourcePath into `.agents/skills/<name>/`
- **AND** validate that a SKILL.md file exists in the source
- **AND** return the installed skill metadata

#### Scenario: Uninstall skill
- **WHEN** `DELETE /api/agents/skills/{name}` is called
- **THEN** the system SHALL remove the `.agents/skills/<name>/` directory
- **AND** return `{success: true}`

#### Scenario: Search marketplace
- **WHEN** `GET /api/agents/skills/search?q=<query>` is called
- **THEN** the system SHALL execute `npx skills find <query>` and parse the output
- **AND** return `{results: [{name, repo, url, description}]}`

### Requirement: Per-Project Skill Selection for Dev Tasks
The DevTask model SHALL support selecting which installed skills the Dev Agent uses during code generation for that specific task.

#### Scenario: Create dev task with skills
- **WHEN** a dev task is created with `skillIds: ["react-native-expo", "voice-live"]`
- **THEN** the task SHALL store the selected skill IDs
- **AND** the Dev Agent SHALL load and inject the content of those skills into Plan and Build prompts

#### Scenario: Auto-suggest skills for spec
- **WHEN** `GET /api/dev/suggest-skills?specId=<id>` is called
- **THEN** the system SHALL match the spec content keywords against installed skill descriptions
- **AND** return the top-3 most relevant skill names

#### Scenario: Skill content injection in pipeline
- **WHEN** the Dev Agent runs a Plan or Build stage for a task with selected skills
- **THEN** it SHALL read each selected skill's SKILL.md and key reference files
- **AND** append condensed skill context (max ~2000 tokens per skill) to the generation prompt
- **AND** the total skill context SHALL NOT exceed 6000 tokens

## MODIFIED Requirements

### Requirement: Agent Skills Configuration
The Turbo Dev Agent SHALL support configurable skills that provide domain-specific knowledge for code generation. Skills are managed via the SkillsService and selected per dev task.

#### Scenario: Skills from local directory
- **WHEN** the dev agent initializes
- **THEN** it SHALL use SkillsService to scan `.agents/skills/` for installed skill definitions
- **AND** include relevant skill instructions as context in code generation prompts based on the task's `skillIds`

#### Scenario: List installed skills
- **WHEN** `GET /api/agents/skills` is called
- **THEN** the system SHALL return a list of installed skills with name, description, version, file count, and source

#### Scenario: Install marketplace skill
- **WHEN** `POST /api/agents/skills/install` is called with repo and skill name
- **THEN** the system SHALL run `npx skills add` in the background and install the skill to `.agents/skills/`

#### Scenario: Delete installed skill
- **WHEN** `DELETE /api/agents/skills/{name}` is called
- **THEN** the system SHALL remove the skill directory and return success
