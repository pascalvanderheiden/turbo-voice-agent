# OSS Documentation

## ADDED Requirements

### Requirement: Project Overview
The README SHALL provide a clear project description that explains what Turbo Voice Agent does, its key features, and its primary use case.

#### Scenario: New user reads README
- **WHEN** a developer discovers the repository
- **THEN** they can understand within 30 seconds what the project does and whether it's relevant to them

### Requirement: Architecture Documentation
The README SHALL include an architecture overview that shows the system components and their relationships.

#### Scenario: Contributor needs architecture context
- **WHEN** a potential contributor wants to understand the system design
- **THEN** they can see the high-level architecture (client → WebSocket → FastAPI → Voice Live API → Azure services) without diving into code

### Requirement: Visual Documentation
The repository SHALL include a screenshot of the running application displayed in the README.

#### Scenario: User wants to see the UI
- **WHEN** a user reviews the README
- **THEN** they can see a screenshot of the main application interface at `docs/screenshot.png`

#### Scenario: Screenshot shows appropriate content
- **WHEN** the screenshot is captured
- **THEN** it SHALL show the main dashboard or voice interface without personal data, cloud URLs, or identifiable information

### Requirement: Prerequisites Documentation
The README SHALL list all prerequisites required to deploy the application.

#### Scenario: Manual deployment prerequisites
- **WHEN** a user wants to deploy manually with `azd up`
- **THEN** the README SHALL list: Azure subscription, Azure CLI (`azd`), Docker Desktop, Node.js, Python 3.12+, Git

#### Scenario: Automated deployment prerequisites
- **WHEN** a user wants to deploy via GitHub Actions
- **THEN** the README SHALL additionally list: GitHub account, Entra ID app registration with OIDC federation

### Requirement: Manual Deployment Instructions
The README SHALL provide step-by-step instructions for deploying via `azd up`.

#### Scenario: First-time manual deployment
- **WHEN** a user follows the manual deployment section
- **THEN** they can successfully deploy the application to Azure by running:
  1. `azd auth login`
  2. Setting required environment variables via `azd env set`
  3. `azd up`

#### Scenario: Environment configuration
- **WHEN** manual deployment requires environment-specific parameters
- **THEN** the README SHALL document each `azd env set` command with parameter descriptions (e.g., `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`)

### Requirement: Automated Deployment Instructions
The README SHALL provide step-by-step instructions for deploying via GitHub Actions with OIDC federation.

#### Scenario: GitHub Actions setup
- **WHEN** a user wants automated deployment
- **THEN** the README SHALL document:
  1. Forking the repository
  2. Creating an Entra ID app registration
  3. Configuring federated credentials for GitHub OIDC
  4. Setting GitHub repository variables
  5. Triggering the deployment workflow

#### Scenario: Repository variables documentation
- **WHEN** setting up GitHub Actions
- **THEN** the README SHALL list all required repository variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_ENV_NAME`, `AZURE_LOCATION`, plus Bicep parameters

### Requirement: Local Development Setup
The README SHALL provide instructions for running the application locally.

#### Scenario: Backend local development
- **WHEN** a developer wants to run the backend locally
- **THEN** the README SHALL document:
  1. Starting Cosmos DB emulator via `docker compose up -d`
  2. Creating `.env` from `.env.example`
  3. Installing dependencies with `pip install -e ".[dev]"`
  4. Running the dev server with `uvicorn app.main:app --reload`

#### Scenario: Frontend local development
- **WHEN** a developer wants to run the frontend locally
- **THEN** the README SHALL document:
  1. Creating `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
  2. Installing dependencies with `npm install`
  3. Running the dev server with `npm run dev`

#### Scenario: Mobile local development
- **WHEN** a developer wants to run the mobile app locally
- **THEN** the README SHALL document:
  1. Installing dependencies with `npm install`
  2. Starting Expo with `npx expo start --ios`

### Requirement: Contributing Guidelines
The README SHALL include a Contributing section that links to the Code of Conduct and describes the contribution process.

#### Scenario: New contributor wants to help
- **WHEN** a developer wants to contribute
- **THEN** the README SHALL direct them to:
  1. Review `CODE_OF_CONDUCT.md`
  2. Fork the repository
  3. Create a feature branch
  4. Submit a pull request
  5. Follow Conventional Commits format

### Requirement: License Documentation
The README SHALL include a License section that identifies the project's license and links to the full license text.

#### Scenario: User checks license
- **WHEN** a user wants to know the license terms
- **THEN** the README SHALL state "MIT License" and link to the `LICENSE` file
