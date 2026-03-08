# Delta Spec: realtime-voice

## MODIFIED Requirements

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
