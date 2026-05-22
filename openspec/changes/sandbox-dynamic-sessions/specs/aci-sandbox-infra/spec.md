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
