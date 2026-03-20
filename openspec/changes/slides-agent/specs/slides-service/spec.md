## ADDED Requirements

### Requirement: Create slide presentation
The system SHALL allow users to create a new slide presentation with a title and optional description. The presentation SHALL be stored with status "draft" and associated with the creating user.

#### Scenario: Create minimal presentation
- **WHEN** user provides a title "Q4 Results"
- **THEN** system creates a presentation with title "Q4 Results", empty description, status "draft", empty sections list, and returns the created resource with generated id

#### Scenario: Create presentation with description
- **WHEN** user provides title "Product Launch" and description "Overview of new features for stakeholders"
- **THEN** system creates a presentation with both fields populated and status "draft"

### Requirement: List slide presentations
The system SHALL return all slide presentations for the authenticated user, ordered by most recently updated first.

#### Scenario: List user presentations
- **WHEN** user requests their presentations
- **THEN** system returns all presentations belonging to that user sorted by updatedAt descending

#### Scenario: Empty list for new user
- **WHEN** user with no presentations requests list
- **THEN** system returns an empty array

### Requirement: Get slide presentation by ID
The system SHALL return a single presentation by its ID, scoped to the authenticated user.

#### Scenario: Get existing presentation
- **WHEN** user requests presentation with valid ID
- **THEN** system returns the full presentation including sections, attachments, and refined draft

#### Scenario: Get non-existent presentation
- **WHEN** user requests presentation with unknown ID
- **THEN** system returns 404 Not Found

### Requirement: Update slide presentation
The system SHALL allow partial updates to a presentation's title, description, sections, images, and attachments.

#### Scenario: Update title only
- **WHEN** user updates presentation with new title "Updated Title"
- **THEN** system updates only the title, preserves all other fields, updates updatedAt timestamp

#### Scenario: Update sections
- **WHEN** user updates presentation with new sections array
- **THEN** system replaces the sections array with the provided data

### Requirement: Delete slide presentation
The system SHALL allow users to delete their own presentations permanently.

#### Scenario: Delete existing presentation
- **WHEN** user deletes presentation by ID
- **THEN** system removes the presentation and returns 204 No Content

#### Scenario: Delete non-existent presentation
- **WHEN** user deletes presentation with unknown ID
- **THEN** system returns 404 Not Found

### Requirement: Upload images and PDFs for context
The system SHALL support images (list of URLs) and attachments (list of URLs) on presentations for use as styling reference or content context during generation.

#### Scenario: Add image to presentation
- **WHEN** user updates presentation with images array containing blob storage URLs
- **THEN** system stores the image URLs on the presentation for use during slide generation

#### Scenario: Add PDF attachment
- **WHEN** user updates presentation with attachments array containing PDF blob URLs
- **THEN** system stores the attachment URLs for content extraction during generation

### Requirement: Link research to presentation
The system SHALL allow users to view research items linked to a presentation, providing research content for incorporation into slides.

#### Scenario: List linked research
- **WHEN** user requests research for a presentation
- **THEN** system returns all research items associated with that presentation

### Requirement: Refine presentation with AI
The system SHALL provide AI-powered refinement that takes the user's description, uploaded files, and linked research to propose a structured slide setup with ordered sections.

#### Scenario: Refine draft presentation
- **WHEN** user triggers refinement on a presentation with description and optional files
- **THEN** system calls AI model with presentation context and returns a structured refined draft with proposed sections, updating status to "refined"

#### Scenario: Stream refinement
- **WHEN** user triggers streaming refinement
- **THEN** system returns an SSE stream of text chunks building the refined draft progressively

#### Scenario: Re-refine already refined presentation
- **WHEN** user triggers refinement on a presentation that already has a refined draft
- **THEN** system generates a new refinement incorporating the latest description, files, and research, replacing the previous refined draft
