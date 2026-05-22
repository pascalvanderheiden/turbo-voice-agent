// session-pool-role.bicep — Grant the backend container app's managed identity
// permission to allocate, forward to, and stop sessions on the pool's management
// endpoint via the "Azure ContainerApps Session Executor" built-in role.
//
// Uses a deterministic guid() role-assignment name to avoid the collision pattern
// documented in .squad/skills/aca-provision-recovery/SKILL.md (manual `az role
// assignment create` produces RANDOM GUIDs that conflict with Bicep's
// deterministic names on the same principal/role/scope triple).

@description('Session pool resource name (used to obtain a scope reference)')
param sessionPoolName string

@description('Principal ID of the backend container app system-assigned managed identity')
param principalId string

// Azure ContainerApps Session Executor — built-in role
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
var sessionExecutorRoleId = '0fb8eba5-a2bb-4abe-b1c1-49dfad359bb0'

resource pool 'Microsoft.App/sessionPools@2025-02-02-preview' existing = {
  name: sessionPoolName
}

resource sessionExecutor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(pool.id, principalId, sessionExecutorRoleId)
  scope: pool
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      sessionExecutorRoleId
    )
    principalType: 'ServicePrincipal'
  }
}
