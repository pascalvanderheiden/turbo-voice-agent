## ADDED Requirements

### Requirement: Search marketplace skills
The system SHALL allow users to search the skills.sh marketplace by keyword query. Results SHALL include skill name, description, repository, and install command.

#### Scenario: Successful marketplace search
- **WHEN** user enters a search query on the skills management page
- **THEN** the system queries skills.sh API and displays matching skills with name, description, and an "Activate" button

#### Scenario: Empty search results
- **WHEN** user enters a query with no marketplace matches
- **THEN** the system displays "No skills found" message

### Requirement: Activate a marketplace skill
The system SHALL allow users to activate a skill from the skills.sh marketplace. Activation SHALL store the skill's metadata and npx install command in Cosmos DB, scoped to the user.

#### Scenario: Activate a skill from search results
- **WHEN** user clicks "Activate" on a marketplace skill
- **THEN** the system stores a Cosmos DB document with: skill name, description, source repo, and npx install command (e.g., `npx @anthropic/skills install <repo>/<skill>`)
- **THEN** the skill appears in the user's activated skills list

#### Scenario: Activate an already-activated skill
- **WHEN** user attempts to activate a skill that is already activated
- **THEN** the system shows a notification that the skill is already active

### Requirement: Deactivate a skill
The system SHALL allow users to deactivate an activated skill. Deactivation SHALL remove the Cosmos DB document for that skill.

#### Scenario: Deactivate an activated skill
- **WHEN** user clicks "Deactivate" on an activated skill
- **THEN** the system removes the skill's Cosmos DB document
- **THEN** the skill no longer appears in the activated skills list
- **THEN** future dev tasks will not include this skill

### Requirement: List activated skills
The system SHALL display all skills activated by the current user, showing name, description, and source repository.

#### Scenario: User has activated skills
- **WHEN** user navigates to the skills management page
- **THEN** the system displays all activated skills with name, description, source, and a "Deactivate" button

#### Scenario: User has no activated skills
- **WHEN** user navigates to the skills management page with no activated skills
- **THEN** the system displays a message prompting them to search and activate skills from the marketplace

### Requirement: Cosmos DB skill document schema
Each activated skill SHALL be stored as a Cosmos DB document with the following fields: `id` (skill name), `userId` (partition key), `docType` ("skill"), `name`, `description`, `source` (repo path), `npxCommand` (the exact npx install command), `activatedAt`, `updatedAt`.

#### Scenario: Skill document structure
- **WHEN** a skill is activated
- **THEN** the Cosmos DB document contains all required fields including the npxCommand field with the exact command to run in the sandbox

### Requirement: No local file storage for skills
The system SHALL NOT store skill files on the backend filesystem or in Azure Blob Storage. The backend SHALL NOT have a `.agents/skills/` directory for activated skills.

#### Scenario: Backend startup without blob sync
- **WHEN** the backend container starts
- **THEN** it does NOT attempt to sync skill files from Blob Storage
- **THEN** it reads activated skill metadata directly from Cosmos DB

### Requirement: Remove local upload capability
The system SHALL NOT provide endpoints for uploading skill files from the user's local machine. The `upload-local` and `install-local` API endpoints SHALL be removed.

#### Scenario: Local upload endpoint removed
- **WHEN** a client sends a POST to `/api/agents/skills/upload-local`
- **THEN** the system returns 404 (endpoint does not exist)
