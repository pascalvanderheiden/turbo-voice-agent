# azure-infrastructure Specification

## Purpose
TBD - created by archiving change add-azure-deployment. Update Purpose after archive.
## Requirements
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

### Requirement: AI Foundry Model Deployments
The infrastructure SHALL provision three Azure AI Foundry instances with all required model deployments, each with project management enabled and a default project.

#### Scenario: East US 2 Foundry instance
- **WHEN** the infrastructure is provisioned
- **THEN** the East US 2 AI Foundry instance SHALL have model deployments: gpt-5.2, gpt-4.1, gpt-4o-transcribe, gpt-5.3-codex, and sora-2

#### Scenario: West US Foundry instance
- **WHEN** the infrastructure is provisioned
- **THEN** the West US AI Foundry instance SHALL have model deployment: o3-deep-research

#### Scenario: Central US Foundry instance
- **WHEN** the infrastructure is provisioned
- **THEN** the Central US AI Foundry instance SHALL have model deployment: gpt-realtime

### Requirement: Managed Identity and RBAC
All service-to-service authentication SHALL use system-assigned managed identity with RBAC role assignments. No API keys SHALL be stored in configuration or environment variables.

#### Scenario: Backend accesses Cosmos DB via managed identity
- **WHEN** the backend makes a Cosmos DB request
- **THEN** it SHALL authenticate using `DefaultAzureCredential` (system-assigned managed identity)
- **AND** the identity SHALL have the `Cosmos DB Built-in Data Contributor` role on the Cosmos DB account

#### Scenario: Backend accesses AI Foundry via managed identity
- **WHEN** the backend makes an Azure OpenAI API call (chat, voice, video generation)
- **THEN** it SHALL authenticate using a token from `DefaultAzureCredential` with scope `https://cognitiveservices.azure.com/.default`
- **AND** the identity SHALL have the `Cognitive Services OpenAI User` role on all three AI Foundry instances

#### Scenario: Container apps pull images via managed identity
- **WHEN** a container app starts or scales
- **THEN** it SHALL pull its Docker image from Azure Container Registry using managed identity with the `AcrPull` role

#### Scenario: Local development fallback
- **WHEN** the application runs locally with `AZURE_OPENAI_API_KEY` or other key env vars set
- **THEN** the application SHALL fall back to API key authentication for developer convenience

### Requirement: Infrastructure as Code
All Azure resources SHALL be defined as Bicep templates and deployable via Azure Developer CLI (`azd up`).

#### Scenario: Full deployment via azd
- **WHEN** a developer runs `azd up` from the project root
- **THEN** all Azure resources SHALL be provisioned, Docker images built and pushed, and container apps deployed with correct environment variables

#### Scenario: Idempotent re-deployment
- **WHEN** `azd up` is run again after initial deployment
- **THEN** only changed resources SHALL be updated and existing data in Cosmos DB and Azure Files SHALL be preserved

