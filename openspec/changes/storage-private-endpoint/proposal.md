## Why

Azure Policy restricts publicly exposed storage accounts — the same issue we resolved for Cosmos DB. The storage account `st2mta7feoalzyq` currently has `networkAcls.defaultAction: 'Allow'`, which exposes it to the public internet and is non-compliant with organizational security policy. We need to add private endpoint access so the Container Apps can reach storage over the private network, making the configuration compliant while keeping Azure Files mounts and blob access working.

## What Changes

- Create private endpoints for the storage account targeting `blob` and `file` sub-resources on the existing `snet-private-endpoints` subnet (already hosting the Cosmos DB private endpoint)
- Create private DNS zones (`privatelink.blob.core.windows.net`, `privatelink.file.core.windows.net`) linked to the CAE VNet
- Update storage network rules: set `defaultAction: 'Deny'`, keep `bypass: 'AzureServices'`
- Ensure Azure Files mount continues to work — `allowSharedKeyAccess: true` must remain for CIFS/SMB mounts in Container Apps
- The storage account key output remains available for the Azure Files volume mount
- Reuse the existing `snet-private-endpoints` subnet — no VNet changes needed

**⚠️ DATA SAFETY**: This change modifies network access rules only. The storage account, file shares, blob containers, and all data remain untouched. Adding private endpoints and denying public access does NOT trigger any data deletion. Deployment must be sequenced: private endpoints + DNS must be active BEFORE public access is denied.

## Capabilities

### New Capabilities
- `storage-private-networking`: Private endpoints (blob + file), private DNS zones, and network ACL lockdown for Storage Account access from Container Apps

### Modified Capabilities
- `azure-infrastructure`: Updated network topology — storage private endpoints added to `snet-private-endpoints` subnet alongside existing Cosmos DB PE

## Impact

- **Infrastructure (Bicep)**: New module `storage-private-endpoint.bicep` for private endpoints + DNS zones. Modified `storage.bicep` (deny public access). Modified `main.bicep` (wire new PE module)
- **Backend**: No code changes — blob SDK uses `DefaultAzureCredential` with the storage account name, DNS handles routing to private IP transparently
- **Frontend**: No changes — does not connect to storage directly
- **Container Apps volumes**: Azure Files mount uses shared key + SMB — private endpoint for `file` sub-resource ensures SMB traffic routes through the VNet. The storage key output in `storage.bicep` continues to work
- **Deployment**: Must use `azd up`. Deployment order matters: provision private endpoints + DNS first, then deny public access
- **Existing data**: Zero risk — network-layer change only, no data migration or account recreation
