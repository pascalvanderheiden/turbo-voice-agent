## ADDED Requirements

### Requirement: Work Account OAuth connection flow
The system SHALL provide OAuth endpoints for connecting a Microsoft Work Account, following the same pattern as the existing Microsoft To-Do connection.

#### Scenario: Initiate connection
- **WHEN** the user calls `POST /api/me/connections/work-account`
- **THEN** the system SHALL return an OAuth authorization URL with scopes `offline_access Mail.Read Calendars.Read Files.Read.All Chat.Read User.Read` and prompt `consent`

#### Scenario: Local dev mode
- **WHEN** `AUTH_DISABLED=true` and the user calls `POST /api/me/connections/work-account`
- **THEN** the system SHALL return `{"connected": true}` with a mock token stored in memory

#### Scenario: OAuth callback success
- **WHEN** Microsoft redirects to `GET /api/auth/callback/work-account?code={code}&state={user_id}`
- **THEN** the system SHALL exchange the code for tokens, store the refresh token (in-memory + Cosmos DB), and redirect to `{FRONTEND_URL}/settings?work_connected=success`

#### Scenario: OAuth callback failure
- **WHEN** the callback receives an error or token exchange fails
- **THEN** the system SHALL redirect to `{FRONTEND_URL}/settings?work_connected=error`

### Requirement: Connection status endpoint
The system SHALL expose `GET /api/me/connections/work-account` returning `{"connected": boolean, "connectedAt": string}`.

#### Scenario: Connected user
- **WHEN** the user has a stored work account refresh token
- **THEN** the endpoint SHALL return `{"connected": true, "connectedAt": "<ISO timestamp>"}`

#### Scenario: Not connected
- **WHEN** no token exists
- **THEN** the endpoint SHALL return `{"connected": false}`

### Requirement: Disconnect flow
The system SHALL provide `DELETE /api/me/connections/work-account` to remove the stored refresh token.

#### Scenario: User disconnects
- **WHEN** the user calls `DELETE /api/me/connections/work-account`
- **THEN** the system SHALL delete the stored token and return `{"connected": false}`

### Requirement: Token storage
The system SHALL store the work account refresh token in the user profile document using `workRefreshToken` and `workConnectedAt` fields, encrypted at rest, mirroring the To-Do token storage pattern.

### Requirement: Settings page connection button
The system SHALL display a "Connect Work Account" button on the settings page.

#### Scenario: Not connected state
- **WHEN** the user visits settings and has no work account connected
- **THEN** the page SHALL show a "Connect Work Account" button with a briefcase icon

#### Scenario: Connected state
- **WHEN** the user has a connected work account
- **THEN** the page SHALL show "Connected · {date}" with a "Disconnect" button

#### Scenario: Callback query param handling
- **WHEN** the settings page loads with `?work_connected=success`
- **THEN** the page SHALL show a success toast and update the connection status

### Requirement: Frontend API functions
The system SHALL expose `connectionsApi.workAccount.status()`, `.connect()`, and `.disconnect()` in the API client, following the same pattern as `connectionsApi.microsoftTodo`.
