## ADDED Requirements

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
