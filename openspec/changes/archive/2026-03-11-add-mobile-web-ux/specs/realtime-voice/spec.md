## ADDED Requirements

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
