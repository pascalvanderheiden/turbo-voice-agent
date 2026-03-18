## ADDED Requirements

### Requirement: Install activated skills in sandbox via npx
The dev agent SHALL install each activated skill in the sandbox by executing its stored npx command as a shell command. This SHALL happen after `openspec init` and before starting the Copilot CLI pipeline.

#### Scenario: Skills installed during pipeline init
- **WHEN** a dev task pipeline starts with activated skills
- **THEN** after `openspec init` completes, the system runs each skill's npx command in the sandbox workspace
- **THEN** skills are installed into `.github/skills/` in the workspace (by the npx command)
- **THEN** the Copilot CLI can access the installed skills during propose/apply stages

#### Scenario: No activated skills
- **WHEN** a dev task pipeline starts with no activated skills
- **THEN** the system skips the skill installation step
- **THEN** the pipeline proceeds directly to the propose/apply stages

### Requirement: Stream skill installation output
The system SHALL stream the output of each skill's npx install command to the frontend via the existing SSE pipeline output. Each skill installation SHALL be clearly labeled in the stream.

#### Scenario: Skill installation visible in stream
- **WHEN** a skill's npx command runs in the sandbox
- **THEN** the stream shows `── install-skill-<name> ──` header
- **THEN** the npx command stdout/stderr is streamed in real-time
- **THEN** success or failure is visible to the user

#### Scenario: Skill installation failure
- **WHEN** a skill's npx command fails (non-zero exit code)
- **THEN** the error is logged and streamed
- **THEN** the pipeline continues with remaining skills (non-blocking)
- **THEN** the pipeline does NOT abort due to a single skill install failure

### Requirement: Skills installed sequentially in sandbox
The system SHALL execute skill npx commands sequentially (one at a time) in the sandbox to avoid npm conflicts and provide clear streaming output.

#### Scenario: Multiple skills installed in order
- **WHEN** a dev task has 3 activated skills
- **THEN** the system installs them one at a time, waiting for each to complete before starting the next
- **THEN** the stream shows distinct headers for each skill installation

### Requirement: Skill installation uses stored npx command
The dev agent SHALL use the exact `npxCommand` field from the Cosmos DB skill document when installing skills in the sandbox. It SHALL NOT construct commands dynamically.

#### Scenario: npx command from Cosmos used as-is
- **WHEN** a skill is being installed in the sandbox
- **THEN** the system sends the exact `npxCommand` value from the skill's Cosmos DB document as a shell command to the sandbox
- **THEN** the command runs in the sandbox workspace directory

### Requirement: Replace tar.gz upload with npx execution
The dev agent SHALL NOT use the `PUT /files/upload` endpoint to install skills. The tar.gz packaging and HTTP upload mechanism SHALL be removed from the skill installation code path.

#### Scenario: No tar.gz upload during skill install
- **WHEN** skills are being installed in a sandbox pipeline
- **THEN** the system does NOT create tar.gz archives
- **THEN** the system does NOT call the sandbox `/files/upload` endpoint for skills
- **THEN** skills are installed solely via npx shell commands

### Requirement: Remove /files/upload endpoint from sandbox
The sandbox server SHALL NOT expose the `PUT /files/upload` endpoint. This endpoint SHALL be removed from `sandbox/server.js`.

#### Scenario: Upload endpoint removed
- **WHEN** a client sends a PUT to `/files/upload`
- **THEN** the sandbox returns 404 (endpoint does not exist)
