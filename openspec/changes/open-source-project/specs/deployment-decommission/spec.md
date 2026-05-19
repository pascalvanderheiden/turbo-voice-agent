# Deployment Decommission

## ADDED Requirements

### Requirement: Azure Environment Teardown
The project maintainer SHALL decommission the existing Azure deployment before finalizing the open-source release.

#### Scenario: Teardown via azd down
- **WHEN** the maintainer is ready to decommission the environment
- **THEN** they SHALL run `azd down --force --purge` to delete all Azure resources

#### Scenario: Purge soft-deleted resources
- **WHEN** running `azd down`
- **THEN** the `--purge` flag SHALL remove soft-deleted resources (e.g., Key Vault) to prevent naming conflicts on redeployment

#### Scenario: Verify clean slate
- **WHEN** the teardown completes
- **THEN** the Azure portal SHALL show no resources remaining in the resource group(s)

### Requirement: Redeployment Validation
After decommissioning, the maintainer SHALL validate that the application can be redeployed from the updated documentation.

#### Scenario: Fresh deployment test
- **WHEN** the environment has been torn down
- **THEN** the maintainer SHALL redeploy using the updated README instructions to verify completeness

#### Scenario: Deployment uses generic parameters
- **WHEN** redeploying
- **THEN** all parameters SHALL be user-provided via `azd env set` or GitHub repo variables (no hardcoded personal values)

### Requirement: Decommission Timing
The decommission SHALL occur immediately before the open-source release to minimize the window between teardown and redeployment validation.

#### Scenario: Avoid premature teardown
- **WHEN** planning the decommission
- **THEN** it MUST NOT occur during active development (wait until all OSS preparation tasks are complete)

#### Scenario: Minimize downtime
- **WHEN** the maintainer is ready to open-source
- **THEN** decommission SHALL be scheduled as the final step before making the repository public
