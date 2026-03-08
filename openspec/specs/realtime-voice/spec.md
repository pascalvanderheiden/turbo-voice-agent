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

