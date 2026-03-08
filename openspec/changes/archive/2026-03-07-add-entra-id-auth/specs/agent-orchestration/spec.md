# Delta Spec: agent-orchestration

## MODIFIED Requirements

### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, spec, dev, skills, and marketing agents. All function calls SHALL include the authenticated user's ID so that specialist agents operate on the correct user's data.

#### Scenario: Route marketing functions
- **WHEN** a function call with name matching marketing operations (create_marketing_video, get_marketing_videos, get_marketing_video, delete_marketing_video, trigger_video_generation) is received
- **THEN** the supervisor routes it to the Marketing Agent and returns the result with agent name "Marketing Agent"

#### Scenario: User context passed to agents
- **WHEN** the supervisor receives a function call from an authenticated session
- **THEN** the supervisor SHALL pass the user_id to the specialist agent
- **AND** the agent SHALL scope all data operations to that user

## ADDED Requirements

### Requirement: Per-User Data Isolation
All backend services SHALL scope data operations to the authenticated user's ID. No user SHALL be able to access, modify, or delete another user's data.

#### Scenario: Notes scoped to user
- **WHEN** a user calls `GET /api/notes`
- **THEN** the service SHALL return only notes belonging to the authenticated user's ID

#### Scenario: Cross-user access prevented
- **WHEN** a user attempts to access a resource (note, idea, spec, dev task, marketing video) belonging to another user
- **THEN** the API SHALL return HTTP 404 (not found) rather than 403 to avoid leaking resource existence

### Requirement: Backend Auth Middleware
The backend SHALL validate Entra ID JWT access tokens on all `/api/*` endpoints and reject unauthenticated requests with HTTP 401.

#### Scenario: Valid token accepted
- **WHEN** a request includes a valid Bearer token from the turboagent.nl tenant
- **THEN** the middleware SHALL extract the user's object ID (oid) and inject it as user_id into the request context

#### Scenario: Missing or invalid token rejected
- **WHEN** a request has no Authorization header or an invalid/expired token
- **THEN** the middleware SHALL return HTTP 401 with error detail "Authentication required"

#### Scenario: Wrong tenant rejected
- **WHEN** a token from a non-turboagent.nl tenant is presented
- **THEN** the middleware SHALL return HTTP 401 with error detail "Invalid tenant"
