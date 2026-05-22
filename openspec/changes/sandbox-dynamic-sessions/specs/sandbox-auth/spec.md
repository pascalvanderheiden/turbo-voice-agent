## MODIFIED Requirements

### Requirement: One-time GitHub auth token connection
The system SHALL provide a flow in the profile settings page for users to connect their GitHub account to the Copilot CLI sandbox by providing a one-time authentication token, following the same pattern as the existing To-Do OAuth connection.

#### Scenario: User connects GitHub token
- **WHEN** a user navigates to profile settings and clicks "Connect GitHub for Sandbox"
- **THEN** the system SHALL present a form to input a GitHub personal access token or initiate an OAuth flow, store the token encrypted in Cosmos DB under the user's profile, and display a "Connected" status

#### Scenario: Token injected on session allocation
- **WHEN** the backend issues the first request that allocates a session for a dev-task and the user has a stored GitHub token
- **THEN** the token SHALL be forwarded to the session as a request header (`X-GH-Token`) that the sandbox entrypoint reads on its first request handler
- **AND** the token SHALL NOT be logged or persisted in session container state beyond the runtime memory

#### Scenario: Sandbox authenticates on first call
- **WHEN** a session receives a request with the `X-GH-Token` header for the first time
- **THEN** the sandbox SHALL run `echo "$token" | gh auth login --with-token` and clear the in-process token variable
- **AND** subsequent calls within the same session SHALL reuse the authenticated `gh` state

#### Scenario: Token not configured
- **WHEN** a user attempts to trigger a dev task without a configured GitHub token
- **THEN** the system SHALL return an error prompting the user to configure their GitHub token in profile settings

### Requirement: Token management
The system SHALL allow users to view connection status, disconnect (revoke), and refresh their GitHub sandbox token from the profile settings page.

#### Scenario: View token status
- **WHEN** a user opens the profile settings page
- **THEN** they SHALL see the GitHub sandbox connection status (connected/disconnected) and the token's creation date

#### Scenario: Disconnect token
- **WHEN** a user clicks "Disconnect" on the GitHub sandbox token
- **THEN** the token SHALL be deleted from Cosmos DB
- **AND** any active session for that user SHALL be stopped via `stopSession` so that subsequent tasks allocate a fresh session without authentication

#### Scenario: Token expiry handling
- **WHEN** a dev task fails because the sandbox GitHub token is expired or revoked
- **THEN** the system SHALL notify the user to reconnect via profile settings and mark the task as failed with an auth error
