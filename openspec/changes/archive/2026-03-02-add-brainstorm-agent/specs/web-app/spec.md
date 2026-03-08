## ADDED Requirements

### Requirement: Brainstorm Ideas Management UI
The web frontend SHALL provide a complete brainstorm ideas management interface with list, create, edit, delete, and refine capabilities.

#### Scenario: Ideas list view
- **WHEN** the user navigates to the Ideas page
- **THEN** a data table SHALL display all ideas with columns: title, status (draft/refined), image count, updated date
- **AND** each row SHALL have action buttons for edit, delete, and refine

#### Scenario: Create idea with images
- **WHEN** the user clicks "New Idea"
- **THEN** a dialog SHALL appear with fields for title, description, and an image upload area (drag & drop, click to browse, camera on mobile)
- **AND** on submit, the idea SHALL be created via the REST API

#### Scenario: Refine idea
- **WHEN** the user clicks "Refine" on an idea
- **THEN** the system SHALL call `POST /api/ideas/{id}/refine` and display the refined draft in a detail view
- **AND** a loading state SHALL be shown during GPT-5.2 processing

#### Scenario: View refined draft
- **WHEN** the user opens a refined idea
- **THEN** the detail view SHALL render the refined draft as formatted markdown alongside the original description and images

### Requirement: Image Upload Component
The web frontend SHALL provide a reusable image upload component used by both notes and ideas.

#### Scenario: Upload via drag and drop
- **WHEN** the user drags an image file onto the upload area
- **THEN** the file SHALL be uploaded to `/api/upload` and a preview thumbnail displayed

#### Scenario: Upload via file browser
- **WHEN** the user clicks the upload area
- **THEN** a file picker SHALL open, filtered to image types

#### Scenario: Remove uploaded image
- **WHEN** the user clicks the remove button on a thumbnail
- **THEN** the image SHALL be removed from the entity's images list

## MODIFIED Requirements

### Requirement: Notes Management UI
The web frontend SHALL provide a complete notes management interface with list, create, edit, and delete capabilities.

#### Scenario: Notes list view
- **WHEN** the user navigates to the Notes page
- **THEN** a data table SHALL display all notes with columns: title, content excerpt, image count (if any), updated date
- **AND** each row SHALL have action buttons for edit and delete

#### Scenario: Create note with images
- **WHEN** the user clicks the "New Note" button
- **THEN** a dialog SHALL appear with fields for title, content, and an image upload area
- **AND** on submit, the note SHALL be created via the REST API with attached image URLs and the list SHALL refresh

#### Scenario: Edit note with images
- **WHEN** the user clicks edit on a note
- **THEN** a dialog SHALL appear with pre-populated title, content, and existing image thumbnails
- **AND** the user can add or remove images
- **AND** on submit, the note SHALL be updated via the REST API

#### Scenario: Delete note
- **WHEN** the user clicks delete on a note
- **THEN** a confirmation dialog SHALL appear
- **AND** on confirmation, the note SHALL be deleted via the REST API and removed from the list

#### Scenario: Loading and error states
- **WHEN** API calls are in progress
- **THEN** the UI SHALL show appropriate loading indicators
- **AND** errors SHALL be displayed as toast notifications using sonner
