# realtime-voice Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
### Requirement: Voice Live WebSocket Proxy
The backend SHALL accept WebSocket connections at `/ws/voice` and proxy audio between the browser and Azure Voice Live. The WebSocket upgrade request SHALL include a valid Entra ID access token as a `token` query parameter for authentication.

#### Scenario: Authenticated voice connection
- **WHEN** a client connects to `/ws/voice?token=<valid_access_token>`
- **THEN** the backend SHALL validate the JWT token
- **AND** establish the voice session with the authenticated user's ID
- **AND** scope all function calls to the user's data

#### Scenario: Unauthenticated voice connection rejected
- **WHEN** a client connects to `/ws/voice` without a token or with an invalid token
- **THEN** the backend SHALL reject the WebSocket upgrade with HTTP 401

#### Scenario: Token expired during voice session
- **WHEN** the user's token expires during an active voice session
- **THEN** the frontend SHALL silently renew the token via MSAL
- **AND** reconnect to `/ws/voice` with the new token

### Requirement: Voice Live Function Calling Bridge
The voice session SHALL expose all supervisor tools including spec operations. The system instructions SHALL mention spec creation, viewing, and idea-to-spec conversion as available capabilities.

#### Scenario: Spec via voice
- **WHEN** a user says "create a spec from my last idea"
- **THEN** the voice agent triggers the generate_spec function through the supervisor

#### Scenario: List specs via voice
- **WHEN** a user asks "what specs do I have?"
- **THEN** the voice agent triggers get_specs and reads back the list

### Requirement: Voice Session Configuration
The voice greeting and system instructions SHALL mention all available capabilities including notes, ideas, research, and specs.

#### Scenario: Updated greeting
- **WHEN** a voice session starts
- **THEN** the greeting mentions the ability to manage notes, ideas, research, and development specs

### Requirement: Client Audio Protocol
Clients (web and iOS) SHALL implement a consistent audio protocol for communicating with the voice WebSocket.

#### Scenario: Web client audio capture
- **WHEN** the user activates voice mode in the web app
- **THEN** the browser SHALL capture microphone audio using the Web Audio API, encode as PCM16 at 24kHz, and stream to the WebSocket in ~50ms chunks

#### Scenario: iOS client audio capture
- **WHEN** the user activates voice mode in the iOS app
- **THEN** the app SHALL capture microphone audio, encode as PCM16 at 24kHz, and stream to the WebSocket in ~50ms chunks

#### Scenario: Audio playback
- **WHEN** the client receives audio data from the WebSocket
- **THEN** the client SHALL queue and play the audio through the device speakers with minimal latency

### Requirement: Voice Session Background Persistence
The voice WebSocket connection SHALL remain active when the browser tab loses visibility (e.g., screen lock, tab switch, app backgrounding on mobile). The session SHALL only terminate when the user explicitly clicks the disconnect/stop button.

#### Scenario: Screen lock does not disconnect voice
- **WHEN** a voice session is active
- **AND** the device screen locks or the browser tab becomes hidden
- **THEN** the WebSocket connection SHALL remain open
- **AND** audio streaming SHALL continue in the background where browser capabilities allow

#### Scenario: Tab switch does not disconnect voice
- **WHEN** a voice session is active
- **AND** the user switches to another browser tab
- **THEN** the WebSocket connection SHALL remain open
- **AND** the session SHALL resume audio capture and playback when the tab regains focus

#### Scenario: AudioContext resume on visibility return
- **WHEN** the browser suspends the AudioContext due to the tab being backgrounded
- **AND** the user returns to the tab
- **THEN** the application SHALL resume the AudioContext automatically
- **AND** audio playback and capture SHALL continue without requiring the user to restart the session

#### Scenario: Explicit disconnect is the only termination
- **WHEN** a voice session is active
- **THEN** the session SHALL only terminate when the user clicks the stop/disconnect button
- **AND** page navigation within the app SHALL NOT disconnect the session (existing overlay behavior)

### Requirement: Screen Wake Lock for Voice
The application SHALL request a Screen Wake Lock when a voice session is active to prevent the device screen from dimming or locking automatically.

#### Scenario: Wake Lock acquired on voice connect
- **WHEN** the user activates voice mode and the connection is established
- **THEN** the application SHALL request a Screen Wake Lock via `navigator.wakeLock.request('screen')`
- **AND** the screen SHALL not auto-dim or auto-lock while voice is active

#### Scenario: Wake Lock released on voice disconnect
- **WHEN** the user disconnects the voice session
- **THEN** the Screen Wake Lock SHALL be released
- **AND** normal screen dimming/locking behavior SHALL resume

#### Scenario: Wake Lock re-acquired on visibility return
- **WHEN** a voice session is active
- **AND** the page regains visibility after being backgrounded
- **THEN** the application SHALL re-acquire the Screen Wake Lock (browsers release it on visibility loss)

#### Scenario: Wake Lock unavailable fallback
- **WHEN** the browser does not support the Screen Wake Lock API
- **THEN** the application SHALL NOT show an error
- **AND** voice mode SHALL function normally without wake lock
- **AND** a subtle informational toast MAY be shown explaining the screen may lock during voice

