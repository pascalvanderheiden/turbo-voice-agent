## MODIFIED Requirements

### Requirement: Token injection at task start
When ACI mode is enabled, the GitHub auth token SHALL be injected into the ACI container via environment variable at container group creation time (not via `gh auth login` after startup). The sandbox entrypoint SHALL run `gh auth login --with-token` using this environment variable before starting the Express server.

#### Scenario: Token injected at ACI creation
- **WHEN** the backend creates an ACI container group for a dev-task and the user has a stored GitHub token
- **THEN** the token is passed as a secure environment variable (`GH_TOKEN`) in the container group definition

#### Scenario: Sandbox authenticates on startup
- **WHEN** the ACI container starts with `GH_TOKEN` set
- **THEN** the entrypoint runs `echo "$GH_TOKEN" | gh auth login --with-token` before starting the server

#### Scenario: No token available
- **WHEN** the user has not connected a GitHub token
- **THEN** the ACI container starts without `GH_TOKEN` and Copilot CLI runs without GitHub authentication
