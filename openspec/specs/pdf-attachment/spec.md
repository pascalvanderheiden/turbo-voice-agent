## Requirements

### Requirement: PDF upload support
The system SHALL accept PDF files via the upload endpoint alongside existing image types.

#### Scenario: User uploads a PDF to an idea
- **WHEN** a user uploads a file with content type `application/pdf` via `POST /api/upload`
- **THEN** the file is stored and a URL path is returned (e.g., `/uploads/<uuid>.pdf`)

#### Scenario: PDF size limit
- **WHEN** a PDF file exceeds 10 MB
- **THEN** the upload is rejected with a 400 error

### Requirement: Idea model attachments field
The Idea model SHALL include an `attachments: list[str]` field for PDF file URLs, separate from the existing `images` field.

#### Scenario: Creating an idea with PDF attachments
- **WHEN** a user creates or updates an idea with PDF URLs in the `attachments` field
- **THEN** the attachments are persisted in Cosmos DB alongside the idea

#### Scenario: Backward compatibility
- **WHEN** an existing idea has no `attachments` field
- **THEN** the field defaults to an empty list

### Requirement: PDF text extraction during refinement
The system SHALL extract text from attached PDFs during idea refinement and include the text as context in the refinement prompt.

#### Scenario: Refinement with PDF attachments
- **WHEN** refinement is triggered on an idea with PDF attachments
- **THEN** the system reads each PDF, extracts text content (up to ~4000 chars per PDF), and includes it in the prompt

#### Scenario: Refinement with no attachments
- **WHEN** refinement is triggered on an idea with no PDF attachments
- **THEN** refinement proceeds normally without PDF context

### Requirement: Frontend PDF upload
The frontend upload component SHALL accept both images and PDF files, displaying a file icon for PDFs instead of a thumbnail.

#### Scenario: User drags a PDF into the upload area
- **WHEN** a user drops a PDF file onto the upload component
- **THEN** the file is uploaded and displayed with a PDF icon and filename

#### Scenario: Mixed uploads
- **WHEN** an idea has both images and PDFs
- **THEN** images show as thumbnails and PDFs show as file icons with names
