# Delta Spec: azure-infrastructure

## MODIFIED Requirements

### Requirement: Azure Container Apps Deployment
The application SHALL be deployed to Azure Container Apps with a backend container (FastAPI) and a frontend container (Next.js standalone) in a shared Container Apps Environment. The backend SHALL include Entra ID configuration environment variables and CORS SHALL be configured with specific allowed origins to support authenticated requests. The frontend SHALL be accessible via a custom domain with managed TLS.

#### Scenario: Backend container app running
- **WHEN** the infrastructure is provisioned via `azd up`
- **THEN** the backend container app SHALL be running with min 1 replica
- **AND** the ingress SHALL expose port 8000 with external access and WebSocket support
- **AND** the idle timeout SHALL be configured to 30 minutes for voice sessions
- **AND** the container SHALL have `ENTRA_TENANT_ID` and `ENTRA_CLIENT_ID` environment variables set
- **AND** CORS SHALL allow credentials with the custom domain and default FQDN as allowed origins

#### Scenario: Frontend container app running
- **WHEN** the infrastructure is provisioned via `azd up`
- **THEN** the frontend container app SHALL be running with min 1 replica
- **AND** the ingress SHALL expose port 3000 with external HTTPS access
- **AND** `NEXT_PUBLIC_API_URL` SHALL point to the backend container app's FQDN
- **AND** the Docker image SHALL be built with `NEXT_PUBLIC_ENTRA_CLIENT_ID` and `NEXT_PUBLIC_ENTRA_TENANT_ID` build arguments

#### Scenario: Custom domain with managed TLS
- **WHEN** the infrastructure is provisioned and DNS records are configured
- **THEN** the frontend container app SHALL be accessible at `https://voice.turboagent.nl`
- **AND** Azure SHALL provision and auto-renew a managed TLS certificate for the custom domain

#### Scenario: Persistent file storage
- **WHEN** the backend container writes files to the data directory
- **THEN** the files SHALL persist across container restarts via an Azure Files volume mount at `/mnt/data`

### Requirement: Azure Cosmos DB Provisioned Throughput
The application SHALL use Azure Cosmos DB NoSQL with provisioned throughput to ensure always-on availability with no cold starts or auto-sleep.

#### Scenario: Database always available
- **WHEN** a request arrives at any time
- **THEN** Cosmos DB SHALL respond without cold start delay because provisioned throughput is always allocated

#### Scenario: Database containers created
- **WHEN** the infrastructure is provisioned
- **THEN** the Cosmos DB account SHALL contain database `turbovoice` with containers: `notes`, `ideas`, `research`, `specs`, `profiles`, each with partition key `/userId` and minimum 400 RU/s provisioned throughput
