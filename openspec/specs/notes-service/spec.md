# notes-service Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
### Requirement: Notes Data Model
The system SHALL store notes in Azure Cosmos DB NoSQL with a defined document schema and Pydantic model hierarchy.

#### Scenario: Note document structure
- **WHEN** a note is stored in Cosmos DB
- **THEN** the document SHALL contain: `id` (UUID), `userId` (partition key), `title` (string, required), `content` (string, required), `images` (list of URL strings, optional, default empty), `docType` ("note"), `createdAt` (ISO 8601), `updatedAt` (ISO 8601)

#### Scenario: Partition key strategy
- **WHEN** notes are queried
- **THEN** all queries SHALL be scoped to the `userId` partition key to avoid cross-partition scans

### Requirement: Cosmos DB Client with Dual Authentication
The system SHALL use a singleton Cosmos DB client that supports both DefaultAzureCredential (Azure) and connection key (emulator) authentication.

#### Scenario: Local development with emulator
- **WHEN** the `COSMOS_ENDPOINT` contains `localhost` or `127.0.0.1`
- **THEN** the client SHALL authenticate using the emulator key with `connection_verify=False`

#### Scenario: Azure deployment
- **WHEN** the `COSMOS_ENDPOINT` points to an Azure Cosmos DB account
- **THEN** the client SHALL authenticate using `DefaultAzureCredential`

### Requirement: Notes Service CRUD Operations
The system SHALL implement a `NotesService` class providing create, read, update, delete, and list operations for notes.

#### Scenario: Create a note
- **WHEN** a create request is received with title, content, and optional images
- **THEN** the service SHALL generate a UUID, set timestamps, and upsert the document to Cosmos DB
- **AND** return the created note

#### Scenario: List notes
- **WHEN** a list request is received
- **THEN** the service SHALL query all notes for the user using a parameterized query scoped to the partition key
- **AND** return the list ordered by `updatedAt` descending

#### Scenario: Get a note by ID
- **WHEN** a get request is received with a note ID
- **THEN** the service SHALL read the document by ID and partition key
- **AND** return the note, or `None` if not found

#### Scenario: Update a note
- **WHEN** an update request is received with a note ID and partial fields (including optional images)
- **THEN** the service SHALL read the existing document, apply the updates, set `updatedAt`, and replace the document
- **AND** return the updated note

#### Scenario: Delete a note
- **WHEN** a delete request is received with a note ID
- **THEN** the service SHALL delete the document by ID and partition key
- **AND** return success confirmation

#### Scenario: Graceful degradation
- **WHEN** the Cosmos DB client is unavailable (emulator not running, connection failure)
- **THEN** the service SHALL return `None` or empty list instead of raising exceptions
- **AND** log the error for debugging

### Requirement: Notes REST API
The system SHALL expose RESTful endpoints for notes CRUD operations.

#### Scenario: POST /api/notes
- **WHEN** a POST request is made to `/api/notes` with `title`, `content`, and optional `images`
- **THEN** the API SHALL create the note and return it with 201 status

#### Scenario: PUT /api/notes/{id}
- **WHEN** a PUT request is made to `/api/notes/{id}` with updated fields including optional `images`
- **THEN** the API SHALL update the note and return it, or 404 if not found

#### Scenario: GET /api/notes
- **WHEN** a GET request is made to `/api/notes`
- **THEN** the API SHALL return a JSON array of all notes for the current user

#### Scenario: GET /api/notes/{id}
- **WHEN** a GET request is made to `/api/notes/{id}`
- **THEN** the API SHALL return the note if found, or 404 if not

#### Scenario: DELETE /api/notes/{id}
- **WHEN** a DELETE request is made to `/api/notes/{id}`
- **THEN** the API SHALL delete the note and return 204, or 404 if not found

### Requirement: Notes Agent
The notes agent SHALL be a specialist agent in the agent team that handles all notes-related tasks using the NotesService.

#### Scenario: Create note via agent
- **WHEN** the notes agent receives a create task with title and content
- **THEN** it SHALL call `NotesService.create()` and return a confirmation with the note details

#### Scenario: List notes via agent
- **WHEN** the notes agent receives a list task
- **THEN** it SHALL call `NotesService.list()` and return a summary of all notes

#### Scenario: Read note via agent
- **WHEN** the notes agent receives a read task with a note identifier
- **THEN** it SHALL call `NotesService.get_by_id()` and return the note content

#### Scenario: Update note via agent
- **WHEN** the notes agent receives an update task with note ID and new content
- **THEN** it SHALL call `NotesService.update()` and return confirmation

#### Scenario: Delete note via agent
- **WHEN** the notes agent receives a delete task with a note identifier
- **THEN** it SHALL call `NotesService.delete()` and return confirmation

