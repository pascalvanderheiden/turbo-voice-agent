# brainstorm-service Specification

## Purpose
TBD - created by archiving change add-brainstorm-agent. Update Purpose after archive.
## Requirements
### Requirement: Idea Data Model
The system SHALL store brainstorm ideas with a defined document schema and Pydantic model hierarchy.

#### Scenario: Idea document structure
- **WHEN** an idea is stored
- **THEN** the document SHALL contain: `id` (UUID), `userId` (partition key), `title` (string, required), `description` (string, required), `images` (list of URL strings, optional), `refinedDraft` (string, optional), `status` (enum: draft/refined), `docType` ("idea"), `createdAt` (ISO 8601), `updatedAt` (ISO 8601)

### Requirement: Brainstorm Service CRUD Operations
The system SHALL implement a `BrainstormService` class providing create, read, update, delete, list, and refine operations for ideas.

#### Scenario: Create an idea
- **WHEN** a create request is received with title, description, and optional images
- **THEN** the service SHALL generate a UUID, set status to "draft", set timestamps, persist the document, and return the created idea

#### Scenario: List ideas
- **WHEN** a list request is received
- **THEN** the service SHALL return all ideas for the user ordered by `updatedAt` descending

#### Scenario: Refine an idea
- **WHEN** a refine request is received for an existing idea
- **THEN** the service SHALL send the idea's title, description, and images to GPT-5.2 via chat completions
- **AND** the GPT-5.2 prompt SHALL instruct the model to: summarize the idea, identify gaps and ask clarifying questions, and produce a development-ready draft
- **AND** the refined output SHALL be stored in the `refinedDraft` field and status set to "refined"
- **AND** if images are attached, they SHALL be included as vision content in the chat completion

#### Scenario: Delete an idea
- **WHEN** a delete request is received with an idea ID
- **THEN** the service SHALL delete the document and return success confirmation

### Requirement: Brainstorm REST API
The system SHALL expose RESTful endpoints for brainstorm idea operations.

#### Scenario: CRUD endpoints
- **WHEN** HTTP requests are made to `/api/ideas` and `/api/ideas/{id}`
- **THEN** the API SHALL support GET (list), GET by ID, POST (create), PUT (update), DELETE operations following the same pattern as notes

#### Scenario: Refine endpoint
- **WHEN** a POST request is made to `/api/ideas/{id}/refine`
- **THEN** the API SHALL trigger GPT-5.2 refinement and return the updated idea with `refinedDraft` populated

### Requirement: Image Upload API
The brainstorm-service SHALL store uploaded images on Azure Blob Storage in production environments. The `/api/upload` endpoint SHALL use Azure Blob Storage with the authenticated user's context for file storage. Skill files (SKILL.md and referenced files) SHALL also be stored on Azure Blob Storage in production, associated with the authenticated user's ID.

#### Scenario: Upload image in production
- **WHEN** a user uploads an image via `/api/upload` in an Azure deployment
- **THEN** the image SHALL be stored in Azure Blob Storage
- **AND** the returned URL SHALL point to the Blob Storage location

#### Scenario: Skill files stored in production
- **WHEN** a skill is installed in an Azure deployment
- **THEN** skill files (SKILL.md, reference files) SHALL be stored in Azure Blob Storage
- **AND** the skill record in Cosmos DB SHALL reference the Blob Storage paths
- **AND** the skill SHALL be associated with the authenticated user's ID (not "default-user")

### Requirement: Brainstorm Agent
The brainstorm agent SHALL be a specialist agent in the agent team that handles all brainstorm-related tasks.

#### Scenario: Create idea via agent
- **WHEN** the brainstorm agent receives a create task with title and description
- **THEN** it SHALL call `BrainstormService.create()` and return confirmation with the idea details

#### Scenario: Refine idea via agent
- **WHEN** the brainstorm agent receives a refine task with an idea ID
- **THEN** it SHALL call `BrainstormService.refine()` and return the refined draft summary

#### Scenario: List ideas via agent
- **WHEN** the brainstorm agent receives a list task
- **THEN** it SHALL call `BrainstormService.list()` and return a summary of all ideas with their status

