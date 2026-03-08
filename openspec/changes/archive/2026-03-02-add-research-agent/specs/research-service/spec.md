## ADDED Requirements

### Requirement: Research Entry Storage
The system SHALL store research entries with title, query, mode, result, citations, and optional idea link.

#### Scenario: Create research entry
- **WHEN** a research is initiated (web search or deep research)
- **THEN** the system SHALL create a research entry with id, title, query, mode (web_search | deep_research), optional ideaId, and timestamps
- **AND** the entry status SHALL be "pending" until results are stored

#### Scenario: Store research results
- **WHEN** the search completes
- **THEN** the system SHALL store the result text (markdown) and a list of citations (url, title) on the research entry
- **AND** the entry status SHALL change to "completed"

### Requirement: Research CRUD Operations
The system SHALL provide REST endpoints for managing research entries.

#### Scenario: List all research
- **WHEN** `GET /api/research` is called
- **THEN** the system SHALL return all research entries ordered by creation date descending

#### Scenario: Get single research
- **WHEN** `GET /api/research/{id}` is called with a valid ID
- **THEN** the system SHALL return the full research entry including result and citations

#### Scenario: Delete research
- **WHEN** `DELETE /api/research/{id}` is called
- **THEN** the system SHALL remove the research entry

#### Scenario: List research by idea
- **WHEN** `GET /api/ideas/{id}/research` is called
- **THEN** the system SHALL return all research entries linked to that idea

### Requirement: Web Search
The system SHALL perform real-time web searches using the Azure OpenAI Responses API with gpt-4.1 and the `web_search_preview` tool.

#### Scenario: Trigger web search
- **WHEN** `POST /api/research/search` is called with a query and optional ideaId
- **THEN** the system SHALL call gpt-4.1 via the Responses API with `web_search_preview` tool
- **AND** parse the response to extract output text and url_citation annotations
- **AND** store the result and citations on the research entry

#### Scenario: Web search response format
- **WHEN** the search completes successfully
- **THEN** the result SHALL be markdown text with inline citations
- **AND** citations SHALL include url and title extracted from the response annotations

### Requirement: Deep Research
The system SHALL perform comprehensive multi-step research using o3-deep-research with the `web_search_preview` tool.

#### Scenario: Trigger deep research
- **WHEN** `POST /api/research/deep` is called with a query and optional ideaId
- **THEN** the system SHALL call o3-deep-research via the Responses API with `web_search_preview` tool
- **AND** the system SHALL handle long-running execution (may take minutes)
- **AND** store the comprehensive result and citations on the research entry

#### Scenario: Deep research uses separate endpoint
- **WHEN** deep research is triggered
- **THEN** the system SHALL use the West US Foundry endpoint (configured via `AZURE_OPENAI_WESTUS_ENDPOINT`)
- **AND** authenticate with the corresponding API key (`AZURE_OPENAI_WESTUS_API_KEY`)

### Requirement: Research-Idea Linking
Research entries SHALL optionally link to a brainstorm idea for contextual enrichment.

#### Scenario: Research linked to idea
- **WHEN** a research is created with an ideaId
- **THEN** the research entry SHALL store the ideaId reference
- **AND** the research SHALL appear in the idea's related research list
