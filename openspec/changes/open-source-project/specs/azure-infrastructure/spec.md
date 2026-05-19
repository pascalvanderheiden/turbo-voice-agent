# Azure Infrastructure

## ADDED Requirements

### Requirement: Generic Bicep parameters
All Bicep templates SHALL use parameters for environment-specific values with no hardcoded personal identifiers.

#### Scenario: No hardcoded GUIDs
- **WHEN** any Bicep file is inspected
- **THEN** it SHALL NOT contain hardcoded subscription IDs, tenant IDs, principal IDs, or personal GUIDs

#### Scenario: Parameters via azure.yaml
- **WHEN** deploying infrastructure
- **THEN** all environment-specific parameters SHALL be declared in `azure.yaml` and set via `azd env set` or passed at deployment time

#### Scenario: Required parameters documented
- **WHEN** a parameter is required for deployment
- **THEN** `azure.yaml` SHALL include a description explaining what the parameter is and how to obtain it

### Requirement: No personal domain references
Infrastructure templates SHALL NOT reference personal or environment-specific domain names.

#### Scenario: Custom domains optional
- **WHEN** deploying infrastructure
- **THEN** custom domain parameters SHALL be optional with default values pointing to `*.azurewebsites.net` or `*.azurecontainerapps.io`

#### Scenario: Certificate parameters optional
- **WHEN** deploying without a custom domain
- **THEN** certificate name parameters SHALL be optional and unused if custom domain is not provided

### Requirement: Personal reference audit
All infrastructure files SHALL be audited for personal references before open-source release.

#### Scenario: Subscription ID removal
- **WHEN** auditing Bicep files
- **THEN** any subscription ID SHALL be replaced with a parameter or removed

#### Scenario: Tenant ID parameterization
- **WHEN** Entra ID tenant IDs are needed
- **THEN** they SHALL be passed as parameters (e.g., `ENTRA_TENANT_ID`)

#### Scenario: Principal ID parameterization
- **WHEN** RBAC role assignments require a principal ID
- **THEN** it SHALL be passed as a parameter (e.g., `DEPLOYER_PRINCIPAL_ID`)

### Requirement: GitHub Actions workflow parameterization
The GitHub Actions deployment workflow SHALL use repository variables for all environment-specific values.

#### Scenario: No hardcoded Azure IDs in workflow
- **WHEN** `.github/workflows/deploy.yml` is inspected
- **THEN** it SHALL NOT contain hardcoded subscription IDs, tenant IDs, client IDs, or resource group names

#### Scenario: Repository variables documented
- **WHEN** a user wants to set up automated deployment
- **THEN** the README SHALL list all required GitHub repository variables with descriptions

#### Scenario: OIDC federation reference
- **WHEN** the workflow uses Azure login
- **THEN** it SHALL use OIDC federated credentials (not stored secrets)
