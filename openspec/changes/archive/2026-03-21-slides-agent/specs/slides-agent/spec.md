## ADDED Requirements

### Requirement: SlidesAgent class with tool definitions
The system SHALL provide a SlidesAgent class that exposes tool definitions for slide presentation CRUD operations and refinement. The agent SHALL follow the same pattern as BrainstormAgent with `__init__`, `tool_definitions` property, and `handle_function_call` method.

#### Scenario: Agent provides tool definitions
- **WHEN** SupervisorAgent queries SlidesAgent for available tools
- **THEN** SlidesAgent returns tool definitions for: create_slides, get_slides_list, get_slides, update_slides, delete_slides, refine_slides

#### Scenario: Agent handles create function call
- **WHEN** SlidesAgent receives a "create_slides" function call with title argument
- **THEN** agent delegates to SlidesService.create() and returns the created presentation

#### Scenario: Agent handles refine function call
- **WHEN** SlidesAgent receives a "refine_slides" function call with slides_id
- **THEN** agent calls refine() method which gathers research context, extracts file content, and calls AI model to produce structured slide sections

### Requirement: Voice-guided slide creation
The system SHALL support voice interaction for creating and refining slide presentations through the SupervisorAgent routing. Users SHALL be able to describe their presentation verbally and receive AI-guided suggestions.

#### Scenario: Voice create slides
- **WHEN** user says "I want to create a presentation about our Q4 results"
- **THEN** SupervisorAgent routes to SlidesAgent which creates a presentation with appropriate title and description extracted from the voice input

#### Scenario: Voice refine slides
- **WHEN** user says "Refine my presentation" while a slides context is active
- **THEN** SupervisorAgent routes to SlidesAgent.refine() which produces structured sections

### Requirement: Research context gathering
The system SHALL gather linked research content when refining slides, summarizing research findings for inclusion in the AI refinement prompt.

#### Scenario: Refine with linked research
- **WHEN** refinement is triggered on a presentation with linked research items
- **THEN** agent fetches research content, summarizes it, and includes it in the refinement prompt for contextually relevant slide content

### Requirement: File content extraction for refinement
The system SHALL extract text content from uploaded PDFs and analyze uploaded images when refining slides, using the extracted content as additional context.

#### Scenario: Refine with PDF attachments
- **WHEN** refinement is triggered on a presentation with PDF attachments
- **THEN** agent extracts text from PDFs and includes relevant content in the refinement prompt

#### Scenario: Refine with image context
- **WHEN** refinement is triggered on a presentation with images
- **THEN** agent analyzes images for visual style cues and includes descriptions in the refinement prompt
