## ADDED Requirements

### Requirement: Web Application Shell
The web frontend SHALL be a Next.js 15 application with Turbo Agent branding, dark mode default, collapsible sidebar navigation, and responsive layout.

#### Scenario: Application loads with branding
- **WHEN** the user opens the web application
- **THEN** the app SHALL display the Turbo Agent logo in the sidebar, use the brand color palette (pink #E91E8C, cyan #00D4FF, purple #7B2FBE), Inter font for UI text, and dark mode as the default theme

#### Scenario: Sidebar navigation
- **WHEN** the user views the sidebar
- **THEN** it SHALL contain navigation items for: Dashboard, Notes, and Voice Mode
- **AND** the sidebar SHALL be collapsible on desktop and off-canvas on mobile

#### Scenario: Theme toggle
- **WHEN** the user toggles the theme
- **THEN** the app SHALL switch between dark and light mode using next-themes

### Requirement: Notes Management UI
The web frontend SHALL provide a complete notes management interface with list, create, edit, and delete capabilities.

#### Scenario: Notes list view
- **WHEN** the user navigates to the Notes page
- **THEN** a data table SHALL display all notes with columns: title, content excerpt (truncated), created date, updated date
- **AND** each row SHALL have action buttons for edit and delete

#### Scenario: Create note
- **WHEN** the user clicks the "New Note" button
- **THEN** a dialog or page SHALL appear with fields for title and content
- **AND** on submit, the note SHALL be created via the REST API and the list SHALL refresh

#### Scenario: Edit note
- **WHEN** the user clicks edit on a note
- **THEN** a dialog or page SHALL appear with pre-populated title and content
- **AND** on submit, the note SHALL be updated via the REST API

#### Scenario: Delete note
- **WHEN** the user clicks delete on a note
- **THEN** a confirmation dialog SHALL appear
- **AND** on confirmation, the note SHALL be deleted via the REST API and removed from the list

#### Scenario: Loading and error states
- **WHEN** API calls are in progress
- **THEN** the UI SHALL show appropriate loading indicators
- **AND** errors SHALL be displayed as toast notifications using sonner

### Requirement: Voice Mode Interface
The web frontend SHALL provide a voice mode page with an animated voice orb and real-time audio communication.

#### Scenario: Voice mode page layout
- **WHEN** the user navigates to Voice Mode
- **THEN** the page SHALL display a centered voice orb on a dark background with minimal surrounding UI

#### Scenario: Voice orb idle state
- **WHEN** the voice session is not active or is waiting for input
- **THEN** the orb SHALL display a subtle breathing pulse animation (1-2s cycle) using the brand gradient

#### Scenario: Voice orb listening state
- **WHEN** the user is speaking (microphone active, speech detected)
- **THEN** the orb SHALL display responsive wave ripples that react to audio input amplitude

#### Scenario: Voice orb thinking state
- **WHEN** the voice agent is processing (between speech stop and response start)
- **THEN** the orb SHALL display a swirling/rotating motion

#### Scenario: Voice orb speaking state
- **WHEN** the voice agent is producing audio output
- **THEN** the orb SHALL display rhythmic pulsing synchronized with the audio output

#### Scenario: Voice orb error state
- **WHEN** a voice connection error occurs
- **THEN** the orb SHALL briefly shake and flash with a red tint

#### Scenario: WebSocket audio connection
- **WHEN** the user activates voice mode
- **THEN** the frontend SHALL open a WebSocket to `/ws/voice`, request microphone permission, capture audio as PCM16 at 24kHz, and stream in ~50ms chunks

#### Scenario: Conversation transcript
- **WHEN** the voice agent speaks or the user speaks
- **THEN** a transcript area below the orb SHALL display the conversation history with user and agent turns

### Requirement: Voice Activation Button
The web frontend SHALL provide a quick-access voice activation button in the site header.

#### Scenario: Voice button in header
- **WHEN** the user is on any page
- **THEN** a circular voice activation button (soundwave icon) SHALL be visible in the site header
- **AND** clicking it SHALL navigate to or activate the voice mode
