# Azure Container Apps Provision Recovery

## When to Use
- `azd up` or `azd provision` fails with "Operation expired" on Container App
- Container App stuck in "Failed" provisioning state with no revisions
- System logs show "Failed to construct registry secret" or ACR authentication 401 errors
- RBAC module didn't execute (check with `az deployment group show -g <rg> -n rbac`)

## Root Cause Pattern
**Bicep dependency ordering catch-22:**
1. Container App resource created with system-assigned managed identity
2. Container App tries to pull image from ACR using managed identity auth
3. ACR authentication fails (401) because RBAC module hasn't run yet
4. RBAC module depends on `containerApp.outputs.principalId`
5. Deployment fails before RBAC executes → no role assignments created

## Diagnosis Steps

### 1. Check Container App State
```bash
az containerapp list -g <resource-group> \
  --query "[].{name:name, state:properties.provisioningState, principalId:identity.principalId}" -o table
```

### 2. Check System Logs for ACR Auth Errors
```bash
az containerapp logs show -n <app-name> -g <resource-group> --type system --tail 50
```
Look for: `"Failed to construct registry secret for registry"` or `"ACR token exchange endpoint returned error status: 401"`

### 3. Verify Identity Has No Role Assignments
```bash
PRINCIPAL_ID="<principal-id-from-step-1>"
az role assignment list --assignee $PRINCIPAL_ID --all -o table
```
If output is empty → RBAC module never ran.

### 4. Verify RBAC Module Didn't Deploy
```bash
az deployment group show -g <resource-group> -n rbac 2>&1
```
If error: `"Deployment 'rbac' could not be found"` → confirms RBAC module was skipped.

### 5. Check ACR for Images
```bash
az acr repository list -n <acr-name> -o table
```
If empty → provisioning failed before `azd deploy` (which builds/pushes images).

## Recovery Steps

### Option A: Manual RBAC Fix + Re-provision (Recommended)

**Step 1:** Manually grant ACR Pull role
```bash
# Get ACR resource ID
ACR_ID=$(az acr show -n <acr-name> --query id -o tsv)

# Get Container App principal ID
PRINCIPAL_ID=$(az containerapp identity show -n <app-name> -g <resource-group> --query principalId -o tsv)

# Grant AcrPull role (ID: 7f951dda-4ed3-4680-a7ca-43fe172d538d)
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "7f951dda-4ed3-4680-a7ca-43fe172d538d" \
  --scope $ACR_ID
```

**Step 2:** Complete provisioning
```bash
azd provision  # Should succeed now that RBAC is fixed
```

**Step 3:** Deploy container images
```bash
azd deploy  # Builds and pushes images, updates Container Apps
```

### Option B: Delete Failed App + Full Re-provision

**Step 1:** Delete failed Container App
```bash
az containerapp delete -n <app-name> -g <resource-group> --yes
```

**Step 2:** Re-run provision (will recreate app)
```bash
azd provision
```
⚠️ **Still requires manual RBAC fix** if Bicep modules not updated.

### Option C: Nuclear Reset (Last Resort)
```bash
azd down --purge  # Deletes all resources
azd up            # Full redeploy
```
⚠️ **DESTRUCTIVE** — only use if Options A/B fail.

## Prevention (Bicep Refactor)

**Problem:** Current `infra/modules/rbac.bicep` is a single monolithic module that depends on all Container Apps being healthy.

**Solution:** Two-phase RBAC:

### Phase 1: ACR Pull Only (Immediate)
Create `infra/modules/rbac-acr-only.bicep`:
```bicep
@description('Backend Container App managed identity principal ID')
param backendPrincipalId string

@description('Frontend Container App managed identity principal ID')
param frontendPrincipalId string

@description('Sandbox Container App managed identity principal ID')
param sandboxPrincipalId string = ''

@description('ACR name')
param acrName string

var acrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrBackendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, backendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

resource acrFrontendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, frontendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: frontendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

resource acrSandboxRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(sandboxPrincipalId)) {
  name: guid(acr.id, sandboxPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: sandboxPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}
```

### Phase 2: Update main.bicep
```bicep
// Immediate ACR access — no health dependency
module acrRbac 'modules/rbac-acr-only.bicep' = {
  name: 'rbac-acr'
  scope: rg
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    sandboxPrincipalId: sandbox.outputs.principalId
    acrName: acr.outputs.name
  }
}

// Full RBAC — runs after ACR access exists
module rbac 'modules/rbac.bicep' = if (deployRbac) {
  name: 'rbac'
  scope: rg
  dependsOn: [acrRbac]  // Explicit ordering
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    cosmosAccountName: cosmos.outputs.name
    acrName: acr.outputs.name  // Keep for non-ACR roles
    storageAccountName: storage.outputs.name
    aiEastUs2Name: aiEastUs2.outputs.name
    aiWestUsName: aiWestUs.outputs.name
    aiCentralUsName: aiCentralUs.outputs.name
    sandboxPrincipalId: sandbox.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
  }
}
```

### Phase 3: Remove ACR Pull from rbac.bicep
In `infra/modules/rbac.bicep`, **delete lines 142-178** (ACR Pull assignments for backend/frontend/sandbox) since they're now in `rbac-acr-only.bicep`.

## Related Issues
- Container App revision provisioning timeout
- "Resource with this name already exists or is in a conflicting state"
- Managed identity authentication to ACR fails on first deploy

## References
- [Azure Container Apps Managed Identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [ACR authentication with Managed Identity](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication-managed-identity)
- [Bicep module dependencies](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/modules#module-dependencies)
