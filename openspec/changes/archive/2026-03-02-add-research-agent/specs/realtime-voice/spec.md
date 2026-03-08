## MODIFIED Requirements

### Requirement: Voice Session Configuration
The Voice Live session SHALL be configured with appropriate voice, model, and audio settings.

#### Scenario: Default session configuration
- **WHEN** a new voice session is established
- **THEN** the session SHALL use `gpt-realtime` model, `shimmer` voice, PCM16 input/output format at 24kHz, ServerVad with relaxed sensitivity, and input audio transcription enabled

#### Scenario: Voice instructions include research capabilities
- **WHEN** the voice session instructions are configured
- **THEN** they SHALL describe the agent's ability to manage notes, brainstorm ideas, AND perform research (web search and deep research)
- **AND** the greeting SHALL mention research as an available capability
