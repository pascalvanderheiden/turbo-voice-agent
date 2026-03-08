## ADDED Requirements

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
The system SHALL expose an upload endpoint for images used by both ideas and notes.

#### Scenario: Upload an image
- **WHEN** a POST multipart request is made to `/api/upload` with an image file
- **THEN** the API SHALL validate the file type (png, jpg, jpeg, gif, webp) and size (max 10MB)
- **AND** store the file with a UUID filename in the uploads directory
- **AND** return the accessible URL

#### Scenario: Serve uploaded images
- **WHEN** a GET request is made to `/uploads/{filename}`
- **THEN** the server SHALL serve the static file

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
