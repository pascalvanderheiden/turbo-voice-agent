## Why

Azure Policy is resetting Cosmos DB's network access to "disabled" after each deployment, breaking the backend API's connection. The current setup uses `publicNetworkAccess: 'Enabled'` with no private networking, which conflicts with the organization's security policies. We need to add private endpoint access so the backend Container App can reach Cosmos DB over a private network, making the configuration compliant with Azure Policy while keeping the service running.

## What Changes

- Add a VNet with dedicated subnets for Container Apps Environment infrastructure and private endpoints
- Configure the Container Apps Environment with VNet integration (internal infrastructure subnet)
- Create a private endpoint for Cosmos DB on a dedicated subnet
- Create a private DNS zone (`privatelink.documents.azure.com`) linked to the VNet so the backend resolves the Cosmos endpoint to the private IP
- Set Cosmos DB `publicNetworkAccess: 'Disabled'` to satisfy Azure Policy
- Peer the new VNet with the existing ACI sandbox VNet (`aci-network.bicep`) to maintain sandbox connectivity
- Update Bicep modules and deployment scripts; manual `azd up` only (no GitHub Actions — quota exhausted)

**⚠️ DATA SAFETY**: This change modifies network access only. The Cosmos DB account, databases, containers, and all data remain untouched. Adding a private endpoint and disabling public access does NOT trigger any data deletion or migration. Deployment must be sequenced: private endpoint + DNS must be active BEFORE public access is disabled.

## Capabilities

### New Capabilities
- `cosmos-private-networking`: Private endpoint, private DNS zone, and VNet integration for Cosmos DB access from Container Apps

### Modified Capabilities
- `azure-infrastructure`: VNet integration for Container Apps Environment, VNet peering with ACI sandbox VNet, updated network topology

## Impact

- **Infrastructure (Bicep)**: New modules for VNet, private endpoint, private DNS zone, VNet peering. Modified `cosmos-db.bicep` (disable public access), `container-apps-env.bicep` (add VNet integration), `main.bicep` (wire new modules)
- **Backend**: No code changes needed — `COSMOS_ENDPOINT` DNS name stays the same, private DNS zone handles resolution to private IP transparently
- **Frontend**: No changes — does not connect to Cosmos directly
- **Deployment**: Must use `azd up` manually (no GitHub Actions quota). Deployment order matters: provision private endpoint + DNS first, then disable public access
- **ACI Sandbox**: Needs VNet peering to maintain connectivity if sandbox accesses backend
- **Existing data**: Zero risk — network-layer change only, no data migration or account recreation
