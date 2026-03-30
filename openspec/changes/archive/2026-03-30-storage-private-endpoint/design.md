## Context

The backend Container App accesses Azure Storage for two purposes:
1. **Azure Files** (`turbodata` share): Mounted as a volume on Container Apps via SMB/CIFS using shared key authentication
2. **Blob Storage** (containers: `skills`, `uploads`, `marketing-videos`, `openspec-imports`): Accessed from backend code via `DefaultAzureCredential`

The storage account currently has `networkAcls.defaultAction: 'Allow'`, meaning it's publicly accessible. Azure Policy restricts this, the same way it restricts publicly exposed Cosmos DB accounts.

**Current state:**
- Storage account: public access allowed, shared key access enabled, TLS 1.2
- Private endpoint subnet (`snet-private-endpoints`, `10.2.2.0/24`) already exists with Cosmos DB PE
- Container Apps Environment is VNet-integrated via `snet-cae-infra`
- Storage key is output from `storage.bicep` for Azure Files volume mount

**Key difference from Cosmos DB:**
- Storage has **multiple sub-resources** (blob, file, table, queue) — each needs its own private endpoint and DNS zone
- We only need `blob` and `file` — table and queue are not used
- Azure Files mount requires `allowSharedKeyAccess: true` and uses SMB protocol — this must work through the file private endpoint

**Constraints:**
- Storage contains production data (file share + blob containers) — zero data loss tolerance
- `allowSharedKeyAccess: true` must remain for CIFS/SMB mounts
- The storage key output must continue working for Container Apps volume configuration
- No backend code changes — DNS-level resolution handles the switch transparently

## Goals / Non-Goals

**Goals:**
- Container Apps reach storage blob and file services exclusively via private endpoints
- Storage `networkAcls.defaultAction` set to `Deny` to satisfy Azure Policy
- Azure Files mount (`turbodata`) continues working through the file private endpoint
- Existing data (file share + blob containers) remains intact
- Deployable via `azd up`

**Non-Goals:**
- Adding private endpoints for table or queue sub-resources (not used)
- Changing backend application code or connection logic
- Adding private endpoints to other services (AI Foundry, ACR)
- Modifying the VNet or subnet topology (reuse existing `snet-private-endpoints`)

## Decisions

### 1. Separate private endpoints per sub-resource

**Decision:** Create two private endpoints — one for `blob` and one for `file` — each with their own private DNS zone.

**Rationale:** Azure Storage requires separate private endpoints per sub-resource type. Each sub-resource gets its own DNS zone (`privatelink.blob.core.windows.net`, `privatelink.file.core.windows.net`). Both endpoints go in the existing `snet-private-endpoints` subnet.

### 2. Single Bicep module for both endpoints

**Decision:** Create one `storage-private-endpoint.bicep` module that provisions both the blob and file private endpoints, both DNS zones, and both VNet links.

**Rationale:** These are tightly coupled — you always need both for this storage account. A single module keeps the `main.bicep` wiring simple (one module call instead of two) and follows the same pattern as `cosmos-private-endpoint.bicep` being self-contained.

### 3. Keep `allowSharedKeyAccess: true`

**Decision:** Retain shared key access on the storage account.

**Rationale:** Azure Container Apps mount Azure Files shares using SMB/CIFS protocol, which requires shared key (storage account key) authentication. The `storageAccountKey` in Container Apps volume configuration does not support managed identity. This is a platform limitation, not a security gap — the key is used only within the VNet.

### 4. Deployment sequence — private endpoints BEFORE denying public access

**Decision:** Deploy in two phases:
- **Phase 1:** Add private endpoints + DNS zones (storage public access stays `Allow`)
- **Phase 2:** Change `defaultAction` to `Deny` (only after verifying private connectivity)

**Rationale:** Same pattern as Cosmos DB. If public access is denied before private endpoints are functional, Container Apps lose connectivity immediately. The two-phase approach ensures the private path works before the public path is removed.

### 5. Reuse existing subnet — no VNet changes

**Decision:** Place both storage private endpoints in the existing `snet-private-endpoints` (`10.2.2.0/24`) subnet.

**Rationale:** A /24 subnet provides 251 usable IPs — more than enough for the Cosmos PE + 2 storage PEs. No changes to `vnet-cae.bicep` needed.

## Risks / Trade-offs

- **[Risk] Azure Files mount interruption during cutover** → If the file private endpoint DNS is not yet propagated when public access is denied, the SMB mount could fail. Mitigation: Phase 2 only after DNS verification.
- **[Risk] Storage key rotation** → The storage key output is captured at deploy time. If the key is rotated, the Container Apps volume mount breaks. This is a pre-existing concern, not introduced by this change.
- **[Trade-off] Two DNS zones for one storage account** → Each sub-resource needs its own zone. This is Azure's design, not optional.
- **[Risk] Subnet IP exhaustion** → Unlikely: 3 private endpoints (1 Cosmos + 2 storage) in a /24 with 251 IPs. Not a real concern.

## Migration Plan

### Phase 1 — Add private networking (public access remains `Allow`)
1. Create `infra/modules/storage-private-endpoint.bicep` with blob PE, file PE, DNS zones, VNet links
2. Update `infra/main.bicep` to wire the new module
3. Run `azd up` — provisions private endpoints and DNS zones
4. Verify: DNS resolves storage hostname to private IP, Container Apps can access blob + file services

### Phase 2 — Deny public access
1. Update `infra/modules/storage.bicep`: change `defaultAction` from `'Allow'` to `'Deny'`
2. Run `azd up`
3. Verify: Container Apps health check passes, Azure Files mount works, blob operations succeed

### Rollback
- Re-enable public access: change `defaultAction` back to `'Allow'` and run `azd up`
- Private endpoints can be deleted without affecting storage data
- No data migration or account recreation involved
