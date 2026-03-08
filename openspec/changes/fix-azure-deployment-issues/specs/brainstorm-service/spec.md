## MODIFIED Requirements

### Requirement: Idea Data Model
The brainstorm-service SHALL store ideas with the authenticated user's ID from the Entra ID token as the `userId` field (partition key). The service SHALL NOT fall back to "default-user" when a valid authentication token is present in the request. All CRUD operations SHALL validate that the userId is extracted from the authentication context before persisting data.

#### Scenario: Create idea with authenticated user
- **WHEN** an authenticated user creates an idea via `POST /api/ideas`
- **THEN** the idea SHALL be stored with the user's Entra ID object ID as `userId`
- **AND** SHALL NOT use "default-user" as the userId

#### Scenario: List ideas for authenticated user
- **WHEN** an authenticated user lists ideas via `GET /api/ideas`
- **THEN** only ideas with the authenticated user's ID SHALL be returned

## MODIFIED Requirements

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
