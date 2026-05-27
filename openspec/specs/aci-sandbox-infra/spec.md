## ADDED Requirements

### Requirement: VNet subnet for ACI delegation
The infrastructure SHALL include a dedicated subnet within the Container Apps Environment VNet, delegated to `Microsoft.ContainerInstance/containerGroups`. The subnet SHALL have a /24 CIDR range to support up to ~250 concurrent container groups.

#### Scenario: Subnet provisioned with ACI delegation
- **WHEN** `azd provision` runs with ACI enabled
- **THEN** a subnet named `snet-aci-sandbox` is created in the VNet with delegation to `Microsoft.ContainerInstance/containerGroups`

### Requirement: User-assigned managed identity for ACI
The infrastructure SHALL create a single user-assigned managed identity shared by all ACI sandbox containers. This identity SHALL have AcrPull on the container registry and Storage Blob Data Reader on the skills storage account.

#### Scenario: Managed identity has ACR pull access
- **WHEN** an ACI container group starts with the user-assigned identity
- **THEN** it can pull the sandbox image from the container registry without explicit credentials

#### Scenario: Managed identity has blob storage access
- **WHEN** the sandbox entrypoint runs `sync-skills.sh` inside an ACI container
- **THEN** it can download skills from the blob storage container using the managed identity

### Requirement: ACI configuration parameters in Bicep
The infrastructure SHALL expose Bicep parameters for ACI container resource limits (CPU, memory), the sandbox Docker image reference, subnet ID, and managed identity resource ID. These SHALL be passed from `main.bicep` to the ACI module.

#### Scenario: Resource limits configurable
- **WHEN** an operator sets `aciSandboxCpu=2` and `aciSandboxMemory=4` in Bicep parameters
- **THEN** ACI container groups are provisioned with 2 vCPUs and 4GB memory

### Requirement: Network security group for ACI subnet
The infrastructure SHALL attach an NSG to the ACI subnet that allows inbound TCP on port 3000 from the Container Apps Environment subnet and denies all other inbound traffic.

#### Scenario: Backend can reach ACI sandbox
- **WHEN** the backend sends an HTTP request to an ACI container's private IP on port 3000
- **THEN** the request is allowed by the NSG

#### Scenario: External traffic is blocked
- **WHEN** any traffic from outside the VNet attempts to reach an ACI container
- **THEN** the NSG denies the traffic
## REMOVED Requirements

### Requirement: VNet subnet for ACI delegation
**Reason**: ACI is removed in favor of Azure Container Apps dynamic sessions. The session pool runs inside the existing Container Apps Environment and does not require a separate delegated subnet.
**Migration**: After the dynamic sessions deployment is verified, delete the `snet-aci-sandbox` subnet and the `aci-network.bicep` module.

### Requirement: User-assigned managed identity for ACI
**Reason**: Sessions pull the sandbox image via the existing managed identity already attached to the Container Apps Environment / ACR. No separate identity is needed.
**Migration**: Delete the user-assigned identity resource and `aci-identity.bicep`. Remove its role assignments on ACR and Blob Storage. The session pool uses the existing identity pattern.

### Requirement: ACI configuration parameters in Bicep
**Reason**: ACI-specific parameters (`aciSandboxCpu`, `aciSandboxMemory`, ACI subnet ID, ACI identity ID) are no longer used. Equivalent settings live on `Microsoft.App/sessionPools` and are covered by the `session-pool-infra` capability.
**Migration**: Remove ACI parameters from `main.bicep`, `main.parameters.json`, and `collect-deployment-params.sh`. Add the equivalent session pool parameters described in `session-pool-infra`.

### Requirement: Network security group for ACI subnet
**Reason**: The ACI subnet is removed. Session pool traffic stays inside the Container Apps Environment and is governed by the existing environment-level network configuration.
**Migration**: Delete the `nsg-vnet-aci-sandbox-*` NSG resource after the ACI subnet is removed.
