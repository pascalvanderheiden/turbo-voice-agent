## 1. VNet and Subnet Setup

- [x] 1.1 Create `infra/modules/vnet-cae.bicep` — VNet `vnet-cae-{env}` with address space `10.2.0.0/16`, subnets: `snet-cae-infra` (`10.2.0.0/23`), `snet-private-endpoints` (`10.2.2.0/24`), `snet-reserved` (`10.2.3.0/24`)
- [x] 1.2 Wire `vnet-cae` module into `infra/main.bicep` with outputs for subnet IDs and VNet ID

## 2. Private Endpoint and DNS

- [x] 2.1 Create `infra/modules/cosmos-private-endpoint.bicep` — private endpoint targeting Cosmos DB `Sql` sub-resource in `snet-private-endpoints` subnet, with private DNS zone `privatelink.documents.azure.com` and DNS zone group for auto A-record registration
- [x] 2.2 Wire `cosmos-private-endpoint` module into `infra/main.bicep`, passing Cosmos DB account ID, VNet ID, and subnet ID

## 3. Container Apps Environment VNet Integration

- [x] 3.1 Update `infra/modules/container-apps-env.bicep` — add `vnetConfiguration` with `infrastructureSubnetId` pointing to `snet-cae-infra` and `internal: false`
- [x] 3.2 Update `infra/main.bicep` to pass the CAE infrastructure subnet ID to the container-apps-env module

## 4. VNet Peering

- [x] 4.1 Add bidirectional VNet peering in `infra/main.bicep` between `vnet-cae` (`10.2.0.0/16`) and the ACI sandbox VNet (`10.1.0.0/16`) with `allowVirtualNetworkAccess: true`

## 5. Phase 1 Deployment — Private Networking (public access stays enabled)

- [x] 5.1 Run `azd up` to provision VNet, private endpoint, DNS zone, CAE VNet integration, and peering
- [x] 5.2 Verify private endpoint connection is approved: `az cosmosdb show --name <name> --resource-group <rg> --query "privateEndpointConnections"`
- [x] 5.3 Verify backend health check passes and can reach Cosmos DB

## 6. Phase 2 — Disable Public Access

- [x] 6.1 Update `infra/modules/cosmos-db.bicep` — change `publicNetworkAccess` from `'Enabled'` to `'Disabled'`
- [x] 6.2 Run `azd up` or `az cosmosdb update --name <name> --resource-group <rg> --public-network-access DISABLED`
- [x] 6.3 Verify backend health check still passes with public access disabled
- [x] 6.4 Verify Cosmos DB data integrity — confirm existing containers and documents are accessible

## 7. Cleanup and Documentation

- [ ] 7.1 Update `openspec/project.md` to reflect new network topology (CAE VNet integration, private endpoint)
- [ ] 7.2 Commit all Bicep changes with descriptive commit message
