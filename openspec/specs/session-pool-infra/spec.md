## ADDED Requirements

### Requirement: Custom-container session pool resource
The infrastructure SHALL provision a `Microsoft.App/sessionPools` resource of `containerType: CustomContainer` inside the existing Container Apps Environment. The pool SHALL use the sandbox image published to the project's Azure Container Registry. The pool SHALL be deployed in the same region as the Container Apps Environment.

#### Scenario: Pool resource exists after azd up
- **WHEN** `azd up` completes successfully
- **THEN** a `Microsoft.App/sessionPools` resource named `sp-sandbox-{token}` SHALL exist in the resource group
- **AND** its `environmentId` SHALL match the existing `cae-*` managed environment
- **AND** its `customContainerTemplate.containers[0].image` SHALL reference the ACR-published sandbox image

#### Scenario: API version pinned
- **WHEN** the Bicep template deploys the pool
- **THEN** it SHALL pin a stable API version (`2024-10-02-preview` or later) and SHALL include container probes when supported

### Requirement: Pool image pulled with managed identity
The session pool SHALL pull the sandbox image from ACR using a user-assigned or system-assigned managed identity that holds the `AcrPull` role on the registry. No registry password SHALL be stored in the pool configuration.

#### Scenario: Pool pulls image without secrets
- **WHEN** the pool refreshes its prewarmed instances after an image push
- **THEN** it SHALL authenticate to ACR via managed identity
- **AND** SHALL NOT use a registry username/password

### Requirement: Session pool capacity configuration
The Bicep template SHALL expose configurable parameters for `maxConcurrentSessions`, `readySessionInstances`, `cooldownPeriodInSeconds`, and per-session `cpu` / `memory`. Defaults SHALL be: `maxConcurrentSessions: 100`, `readySessionInstances: 1`, `cooldownPeriodInSeconds: 600`, `cpu: 2`, `memory: "4Gi"`.

#### Scenario: Defaults applied when no overrides
- **WHEN** the operator does not override any pool parameter
- **THEN** the pool SHALL be deployed with the documented defaults

#### Scenario: Override accepted
- **WHEN** the operator sets `sessionPoolReadyInstances=3` via Bicep parameters
- **THEN** the deployed pool SHALL keep at least 3 prewarmed sessions

### Requirement: Container probes for session health
The session pool SHALL define a `Startup` probe on `GET /ready` and a `Liveness` probe on `GET /health`, both on port 3000. The pool SHALL automatically remove and replace any session instance that fails its probes.

#### Scenario: Healthy session passes probes
- **WHEN** a newly warmed session completes its skills sync
- **THEN** `GET /ready` SHALL return 200 within 30 probe attempts
- **AND** `GET /health` SHALL return 200 throughout the session's lifetime

#### Scenario: Unhealthy session replaced
- **WHEN** a session's liveness probe fails 3 consecutive times
- **THEN** the session pool SHALL remove that instance and warm a replacement to maintain `readySessionInstances`

### Requirement: RBAC for backend to invoke sessions
The infrastructure SHALL assign the `Azure ContainerApps Session Executor` role on the session pool resource to the backend container app's system-assigned managed identity. This role SHALL grant permission to allocate sessions, forward requests, and stop sessions via the pool management endpoint.

#### Scenario: Backend can allocate sessions
- **WHEN** the backend acquires an Entra token for `https://dynamicsessions.io/.default`
- **THEN** it SHALL be authorized to call the pool management endpoint
- **AND** SHALL be able to allocate and stop sessions for any identifier

#### Scenario: Role assignment scoped to pool only
- **WHEN** the role assignment is created
- **THEN** its scope SHALL be the session pool resource ID (not the subscription or resource group)

### Requirement: Bicep outputs for backend configuration
The Bicep template SHALL output `sessionPoolManagementEndpoint` and `sessionPoolName`. These outputs SHALL be set as environment variables on the backend container app as `SESSION_POOL_MANAGEMENT_ENDPOINT` and `SESSION_POOL_NAME`.

#### Scenario: Backend env vars populated from outputs
- **WHEN** `azd up` completes
- **THEN** the backend container app's environment SHALL include `SESSION_POOL_MANAGEMENT_ENDPOINT` set to the pool's `poolManagementEndpoint` value
- **AND** `SESSION_POOL_NAME` set to the pool resource name
