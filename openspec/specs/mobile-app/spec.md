# mobile-app Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
### Requirement: iOS Mobile Application Shell
The iOS app SHALL be built with React Native 0.82+ / Expo SDK 52+ using New Architecture, TypeScript, and Turbo Agent branding.

#### Scenario: Application loads with branding
- **WHEN** the user opens the iOS app
- **THEN** the app SHALL use the Turbo Agent color palette, Inter font, and dark mode as the default theme

#### Scenario: Tab navigation
- **WHEN** the user views the app
- **THEN** a tab bar SHALL provide navigation between Notes and Voice tabs

### Requirement: iOS Notes Management
The iOS app SHALL provide notes management with list, create, edit, and delete capabilities matching the web app.

#### Scenario: Notes list screen
- **WHEN** the user opens the Notes tab
- **THEN** a scrollable list SHALL display all notes with title, content excerpt, and updated date
- **AND** pull-to-refresh SHALL reload the notes from the API

#### Scenario: Create note on iOS
- **WHEN** the user taps the create button
- **THEN** a form screen SHALL appear with title and content fields
- **AND** on submit, the note SHALL be created via the REST API

#### Scenario: Edit note on iOS
- **WHEN** the user taps a note in the list
- **THEN** a detail/edit screen SHALL appear with pre-populated fields
- **AND** on save, the note SHALL be updated via the REST API

#### Scenario: Delete note on iOS
- **WHEN** the user swipes a note or taps delete
- **THEN** a confirmation alert SHALL appear
- **AND** on confirmation, the note SHALL be deleted via the REST API

### Requirement: iOS Voice Mode
The iOS app SHALL provide a voice mode screen with the same voice orb and audio capabilities as the web app.

#### Scenario: Voice mode screen
- **WHEN** the user navigates to the Voice tab
- **THEN** the screen SHALL display a centered voice orb with the same five state animations as the web app (idle, listening, thinking, speaking, error)

#### Scenario: iOS audio capture
- **WHEN** the user activates voice mode
- **THEN** the app SHALL request microphone permission, capture audio as PCM16 at 24kHz, and stream to the backend WebSocket

#### Scenario: iOS audio playback
- **WHEN** the app receives response audio from the WebSocket
- **THEN** the app SHALL play the audio through the device speaker with minimal latency

#### Scenario: Conversation transcript on iOS
- **WHEN** voice conversation is active
- **THEN** a scrollable transcript area SHALL display the conversation history below the orb

### Requirement: Development Screen
The mobile application SHALL provide a Development screen accessible from the More menu for viewing development tasks with mode indicators and iteration progress, matching the web app's functionality.

#### Scenario: View development tasks
- **WHEN** the user navigates to Development from the More menu
- **THEN** the screen SHALL display all dev tasks as cards
- **AND** each card SHALL show title, status, and a 4-stage progress indicator

#### Scenario: Dev list shows mode
- **WHEN** a user views the development task list on mobile
- **THEN** each task SHALL display a mode badge ("Mock" or "Sequence")
- **AND** sequence tasks SHALL show iteration progress

#### Scenario: Dev detail shows iterations
- **WHEN** a user views a sequence mode task detail on mobile
- **THEN** iterations SHALL be displayed as collapsible sections
- **AND** each iteration SHALL show its label and stage pipeline with Ionicons

#### Scenario: Plan output display
- **WHEN** a user taps on a completed Plan stage
- **THEN** the plan output SHALL be displayed as formatted text below the stage

#### Scenario: View development task detail
- **WHEN** the user taps a dev task
- **THEN** the detail screen SHALL show pipeline stage progress, stage outputs, and screenshot artifacts

### Requirement: Spec Detail Development Action
The mobile spec detail screen SHALL provide a "Develop" action to create linked dev tasks.

#### Scenario: Create dev task from spec on mobile
- **WHEN** a user taps "Develop" on a spec detail screen
- **THEN** an action sheet SHALL appear to choose the pipeline mode (Mock or Sequence)
- **AND** upon selection, a dev task SHALL be created and the user navigated to the dev detail screen

