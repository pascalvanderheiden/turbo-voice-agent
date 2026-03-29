## Context

The backend Container App connects to Cosmos DB over the public internet using `DefaultAzureCredential` (managed identity, no API keys). The Cosmos DB account currently has `publicNetworkAccess: 'Enabled'` and `disableLocalAuth: true`.

An Azure Policy in the organization keeps resetting Cosmos DB network access to "disabled" after deployments, severing the backend's connection. The fix is to route traffic through a private endpoint so the backend never needs public network access.

**Current state:**
- Cosmos DB: public access enabled, RBAC-only auth, continuous backup (7-day)
- Container Apps Environment: no VNet integration (managed networking)
- One VNet exists for ACI sandbox (`10.1.0.0/16`, `snet-aci-sandbox` subnet)
- Backend env var `COSMOS_ENDPOINT` points to the public Cosmos endpoint (e.g., `https://cosmos-xxx.documents.azure.com:443/`)

**Constraints:**
- Cosmos DB contains production data — zero data loss tolerance
- No GitHub Actions quota — must deploy manually via `azd up`
- Backend code must NOT change — DNS-level resolution handles the switch transparently

## Goals / Non-Goals

**Goals:**
- Backend Container App reaches Cosmos DB exclusively via private endpoint
- Cosmos DB `publicNetworkAccess` set to `Disabled` to satisfy Azure Policy
- Existing data remains intact throughout the change
- ACI sandbox VNet maintains connectivity via peering
- Deployable via `azd up` (no CI/CD dependency)

**Non-Goals:**
- Migrating Cosmos DB to a different account or region
- Adding private endpoints to other services (AI Foundry, ACR, etc.)
- Making the Container Apps Environment fully internal (frontend still needs public ingress)
- Changing backend application code or connection logic

## Decisions

### 1. New VNet for Container Apps Environment

**Decision:** Create a new VNet (`vnet-cae`, `10.2.0.0/16`) with three subnets rather than reusing the ACI VNet.

**Rationale:** The ACI VNet's subnet is delegated to `Microsoft.ContainerInstance/containerGroups` — it cannot host Container Apps infrastructure or private endpoints. A separate VNet with peering keeps concerns isolated and avoids modifying existing ACI networking.

**Subnets:**
| Subnet | CIDR | Purpose |
|--------|------|---------|
| `snet-cae-infra` | `10.2.0.0/23` | Container Apps Environment infrastructure (requires /23 minimum) |
| `snet-private-endpoints` | `10.2.2.0/24` | Private endpoints (Cosmos DB) |
| `snet-reserved` | `10.2.3.0/24` | Reserved for future private endpoints |

**Alternative considered:** Reuse ACI VNet with additional subnets — rejected because modifying the ACI-delegated subnet risks breaking sandbox containers.

### 2. Container Apps Environment VNet integration

**Decision:** Add `vnetConfiguration` to the existing Container Apps Environment with `internal: false`.

**Rationale:** Setting `internal: false` keeps the CAE's public ingress for frontend/backend (custom domain still works) while placing the environment's infrastructure inside the VNet. This allows outbound traffic from backend containers to route through the VNet to the Cosmos private endpoint.

**Alternative considered:** `internal: true` — rejected because it would break public access to frontend and require a load balancer/Application Gateway for ingress.

### 3. Private endpoint + Private DNS zone for Cosmos DB

**Decision:** Create a private endpoint in `snet-private-endpoints` targeting the Cosmos DB account, with a private DNS zone `privatelink.documents.azure.com` linked to the CAE VNet.

**Rationale:** The private DNS zone ensures that when the backend resolves `cosmos-xxx.documents.azure.com`, it gets the private IP (e.g., `10.2.2.4`) instead of the public IP. No backend code changes needed — `COSMOS_ENDPOINT` stays the same.

### 4. VNet peering between CAE VNet and ACI VNet

**Decision:** Create bidirectional VNet peering between the new CAE VNet (`10.2.0.0/16`) and the existing ACI VNet (`10.1.0.0/16`).

**Rationale:** The ACI sandbox may need to reach the backend Container App over the internal network. Peering ensures connectivity without overlapping address spaces.

### 5. Deployment sequence — private endpoint BEFORE disabling public access

**Decision:** Deploy in two phases to ensure zero downtime:
- **Phase 1:** Add VNet, private endpoint, DNS zone, CAE VNet integration (Cosmos public access stays enabled)
- **Phase 2:** Disable Cosmos DB public access (only after verifying private connectivity)

**Rationale:** If public access is disabled before the private endpoint is functional, the backend loses connectivity immediately. The two-phase approach ensures the private path is working before the public path is removed.

**Alternative considered:** Single deployment — rejected because Bicep deployment ordering doesn't guarantee the private endpoint is fully provisioned before the Cosmos account property changes.

## Risks / Trade-offs

- **[Risk] CAE VNet integration is a destructive update** → The Container Apps Environment may need to be recreated to add VNet integration if the existing one doesn't support in-place updates. Mitigation: Test with `azd up` first; if it fails, the CAE must be recreated (container apps will be redeployed but Cosmos data is unaffected).
- **[Risk] DNS propagation delay** → After creating the private DNS zone, it may take a few minutes for resolution to switch. Mitigation: Phase 2 (disable public access) should be run only after verifying `nslookup` resolves to the private IP.
- **[Risk] ACI sandbox connectivity** → If ACI containers need to reach Cosmos directly (they currently don't), they'd need the DNS zone linked to their VNet too. Mitigation: Current architecture routes all Cosmos access through the backend API, so this is not an issue.
- **[Trade-off] Two VNets + peering vs single VNet** → Slightly more complex topology, but avoids touching the working ACI setup.

## Migration Plan

### Phase 1 — Add private networking (public access remains enabled)
1. Create new Bicep modules: `vnet-cae.bicep`, `cosmos-private-endpoint.bicep`
2. Update `container-apps-env.bicep` with `vnetConfiguration`
3. Update `main.bicep` to wire new modules
4. Run `azd up` — this provisions VNet, subnets, private endpoint, DNS zone, peering, and updates CAE
5. Verify: `az cosmosdb show` confirms private endpoint connection, backend health check passes

### Phase 2 — Disable public access
1. Update `cosmos-db.bicep`: set `publicNetworkAccess: 'Disabled'`
2. Run `azd up` again — or use `az cosmosdb update --name <name> --resource-group <rg> --public-network-access DISABLED`
3. Verify: backend health check still passes, Cosmos is only reachable via private endpoint

### Rollback
- Re-enable public access: `az cosmosdb update --public-network-access ENABLED`
- Remove VNet integration from CAE if needed (may require recreation)
- Private endpoint can be deleted without affecting Cosmos data

## Open Questions

- Does the current Container Apps Environment support in-place VNet integration, or will it need recreation? (Test with `azd up` — if it fails with a conflict, we'll need to handle CAE recreation)
- Are there any other Azure Policies that might block private endpoint creation or VNet peering?
