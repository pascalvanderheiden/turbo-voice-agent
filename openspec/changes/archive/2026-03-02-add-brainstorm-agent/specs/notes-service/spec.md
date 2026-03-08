## MODIFIED Requirements

### Requirement: Notes Data Model
The system SHALL store notes in Azure Cosmos DB NoSQL with a defined document schema and Pydantic model hierarchy.

#### Scenario: Note document structure
- **WHEN** a note is stored in Cosmos DB
- **THEN** the document SHALL contain: `id` (UUID), `userId` (partition key), `title` (string, required), `content` (string, required), `images` (list of URL strings, optional, default empty), `docType` ("note"), `createdAt` (ISO 8601), `updatedAt` (ISO 8601)

#### Scenario: Partition key strategy
- **WHEN** notes are queried
- **THEN** all queries SHALL be scoped to the `userId` partition key to avoid cross-partition scans

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
