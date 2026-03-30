## 1. Create Storage Private Endpoint Bicep Module

- [x] 1.1 Create `infra/modules/storage-private-endpoint.bicep` — two private endpoints (blob + file) targeting the storage account in `snet-private-endpoints` subnet, with private DNS zones (`privatelink.blob.core.windows.net`, `privatelink.file.core.windows.net`), VNet links, and DNS zone groups for auto A-record registration. Follow the pattern in `cosmos-private-endpoint.bicep`. Parameters: `name`, `location`, `storageAccountId`, `storageAccountName`, `subnetId`, `vnetId`.

## 2. Wire Storage Private Endpoint into main.bicep

- [x] 2.1 Add a `storagePrivateEndpoint` module call in `infra/main.bicep`, passing the storage account ID/name, VNet ID, and private endpoints subnet ID from existing module outputs. Place it after the `storage` module and `vnetCae` module.

## 3. Phase 1 Deployment — Private Endpoints (public access stays Allow)

- [x] 3.1 Run `azd up` to provision storage private endpoints and DNS zones
- [x] 3.2 Verify private endpoint connections are approved and DNS resolves to private IPs
- [x] 3.3 Verify Container Apps can access blob storage and Azure Files mount works

## 4. Deny Public Access on Storage Account

- [x] 4.1 Update `infra/modules/storage.bicep` — change `networkAcls.defaultAction` from `'Allow'` to `'Deny'`

## 5. Phase 2 Deployment — Deny Public Access

- [x] 5.1 Run `azd up` to apply the network ACL change
- [x] 5.2 Verify Container Apps health check passes, blob operations work, and Azure Files mount remains functional
- [x] 5.3 Verify all existing data (blob containers + file share) is intact and accessible

## 6. Update Documentation

- [x] 6.1 Update `openspec/project.md` network topology section to reflect storage private endpoints in `snet-private-endpoints` alongside Cosmos DB PE
