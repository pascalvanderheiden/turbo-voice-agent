## MODIFIED Requirements

### Requirement: Sandbox Container App infrastructure
The system SHALL provision a dedicated Container App for the GitHub Copilot CLI sandbox as part of the Azure infrastructure, including container image configuration, networking, identity, and scaling.

#### Scenario: Sandbox Container App deployed via Bicep
- **WHEN** `azd provision` or `azd up` is executed
- **THEN** a Container App named `ca-sandbox-{env}` SHALL be created in the existing Container Apps Environment with Docker-in-Docker support, the Copilot CLI pre-installed, and a managed identity for accessing shared resources

#### Scenario: Network isolation
- **WHEN** the sandbox Container App is deployed
- **THEN** ingress SHALL be restricted to internal traffic from the backend Container App only (no external access), and the sandbox SHALL have outbound access to GitHub and npm registries

#### Scenario: Sandbox scaling
- **WHEN** the sandbox Container App is configured
- **THEN** it SHALL have min 1 / max 5 replicas with HTTP-based scaling to support concurrent dev task execution

#### Scenario: Sandbox connectivity via VNet peering
- **WHEN** the Container Apps Environment has VNet integration and peering is established with the ACI VNet
- **THEN** the sandbox Container App SHALL be able to communicate with ACI sandbox containers over the peered VNet

### Requirement: Cosmos DB container for sandbox state
The system SHALL add a Cosmos DB container to store sandbox configuration and task state per user.

#### Scenario: Sandbox state container provisioned
- **WHEN** infrastructure is provisioned
- **THEN** a Cosmos DB container named `sandbox_state` SHALL be created with partition key `/userId` and 400 RU/s throughput

#### Scenario: Sandbox state accessible via private endpoint
- **WHEN** the Cosmos DB private endpoint is active and public access is disabled
- **THEN** the sandbox state container SHALL remain accessible from the backend Container App via the private endpoint

### Requirement: Sandbox Docker image in ACR
The system SHALL build and store the sandbox Docker image in the existing Azure Container Registry.

#### Scenario: Sandbox image pushed to ACR
- **WHEN** the CI/CD pipeline runs with sandbox changes
- **THEN** a Docker image containing the GitHub Copilot CLI, Node.js, Playwright, and OpenSpec CLI SHALL be built and pushed to the ACR
