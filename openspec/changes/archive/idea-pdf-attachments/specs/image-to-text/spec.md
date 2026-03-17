## ADDED Requirements

### Requirement: Mistral Document AI deployment
The system SHALL use a deployed `mistral-document-ai-2512` model in Azure AI Foundry (East US 2) for extracting text descriptions from images.

#### Scenario: Model availability
- **WHEN** the backend starts
- **THEN** the Mistral Document AI endpoint is configured via `MISTRAL_DOCUMENT_AI_ENDPOINT` environment variable

### Requirement: Image description extraction during refinement
The system SHALL extract text descriptions from attached images using Mistral Document AI during refinement, replacing raw base64 image content in the prompt.

#### Scenario: Refinement with image attachments
- **WHEN** refinement is triggered on an idea with image attachments
- **THEN** each image is sent to Mistral Document AI to extract a text description, and the descriptions are included in the refinement prompt

#### Scenario: Mistral service unavailable
- **WHEN** the Mistral Document AI endpoint is not configured or returns an error
- **THEN** the system falls back to the existing behavior (base64 image sent to GPT via vision)

#### Scenario: Multiple images
- **WHEN** an idea has multiple images
- **THEN** all images are processed in parallel and their descriptions are included in order
