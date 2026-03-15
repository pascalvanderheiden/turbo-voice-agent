## ADDED Requirements

### Requirement: Microsoft Account OAuth connection flow
The system SHALL provide an "Authenticate Once" endpoint at `POST /api/me/connections/microsoft-todo` that initiates the Microsoft OAuth consent flow for `Tasks.ReadWrite` scope. Upon successful consent, the server SHALL securely store the refresh token associated with the user's profile.

#### Scenario: User initiates connection
- **WHEN** the user clicks "Connect Microsoft To-Do" and the backend receives `POST /api/me/connections/microsoft-todo`
- **THEN** the system SHALL return an OAuth authorization URL that the frontend redirects to

#### Scenario: OAuth callback completes successfully
- **WHEN** Microsoft redirects back with an authorization code to `GET /api/auth/callback/microsoft-todo`
- **THEN** the system SHALL exchange the code for tokens, store the refresh token encrypted and associated with the user, and redirect to the frontend with a success indicator

#### Scenario: OAuth callback fails
- **WHEN** the callback receives an error parameter or token exchange fails
- **THEN** the system SHALL redirect to the frontend with an error indicator and NOT store any tokens

### Requirement: Connection status endpoint
The system SHALL expose the Microsoft To-Do connection status via `GET /api/me/connections/microsoft-todo` returning `{"connected": true/false, "connectedAt": "..."}`.

#### Scenario: User is connected
- **WHEN** the user has a valid stored refresh token for Microsoft To-Do
- **THEN** the endpoint SHALL return `{"connected": true, "connectedAt": "<ISO timestamp>"}`

#### Scenario: User is not connected
- **WHEN** the user has no stored token
- **THEN** the endpoint SHALL return `{"connected": false}`

### Requirement: Disconnect flow
The system SHALL provide `DELETE /api/me/connections/microsoft-todo` to revoke access and remove the stored refresh token.

#### Scenario: User disconnects
- **WHEN** the user requests disconnect via `DELETE /api/me/connections/microsoft-todo`
- **THEN** the system SHALL delete the stored refresh token and return `{"connected": false}`

### Requirement: Token storage security
The system SHALL encrypt stored refresh tokens at rest. Tokens SHALL be stored in the user profile document in Cosmos DB (or in-memory store during local dev) and SHALL NOT be exposed via any API response.

#### Scenario: Token is stored encrypted
- **WHEN** the OAuth flow completes and a refresh token is stored
- **THEN** the token SHALL be encrypted before persistence and the raw token SHALL NOT appear in any API response or log output
