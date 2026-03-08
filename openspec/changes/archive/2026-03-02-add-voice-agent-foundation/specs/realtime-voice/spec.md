## ADDED Requirements

### Requirement: Voice Live WebSocket Proxy
The backend SHALL expose a WebSocket endpoint at `/ws/voice` that proxies audio between the client and Azure Voice Live API, keeping Azure credentials server-side.

#### Scenario: Client connects and starts voice session
- **WHEN** a client opens a WebSocket connection to `/ws/voice`
- **THEN** the backend establishes a Voice Live SDK session with Azure, configured with ServerVad turn detection, PCM16 24kHz audio format, noise suppression (`azure_deep_noise_suppression`), and echo cancellation

#### Scenario: Client streams audio input
- **WHEN** the client sends PCM16 audio chunks over the WebSocket
- **THEN** the backend forwards the audio to the Voice Live input audio buffer

#### Scenario: Voice Live produces response audio
- **WHEN** the Voice Live session emits `RESPONSE_AUDIO_DELTA` events
- **THEN** the backend streams the audio data back to the client over the WebSocket

#### Scenario: Barge-in handling
- **WHEN** `INPUT_AUDIO_BUFFER_SPEECH_STARTED` is received while a response is active
- **THEN** the backend SHALL cancel the active response via `connection.response.cancel()`

### Requirement: Voice Live Function Calling Bridge
The backend SHALL handle function calls from Voice Live by routing them through the supervisor agent and returning results to the voice session.

#### Scenario: Voice Live triggers a function call
- **WHEN** the Voice Live session emits `RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE`
- **THEN** the backend SHALL parse the function name and arguments, invoke the supervisor agent with the request, and send the result back as a `FunctionCallOutputItem`
- **AND** request a new response from Voice Live with `connection.response.create()`

#### Scenario: Function call fails
- **WHEN** the supervisor agent raises an exception during function execution
- **THEN** the backend SHALL return an error result to Voice Live with a user-friendly message
- **AND** the voice agent SHALL communicate the error to the user naturally

### Requirement: Voice Session Configuration
The Voice Live session SHALL be configured with appropriate voice, model, and audio settings.

#### Scenario: Default session configuration
- **WHEN** a new voice session is established
- **THEN** the session SHALL use `gpt-realtime` model, `en-US-Ava:DragonHDLatestNeural` voice, PCM16 input/output format at 24kHz, ServerVad with 500ms silence duration, and input audio transcription enabled

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
