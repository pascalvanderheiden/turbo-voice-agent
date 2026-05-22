// session-pool-identity.bicep — User-assigned managed identity for the
// dynamic session pool, with AcrPull pre-granted on the registry BEFORE
// the pool is created.
//
// Why a UAMI (not system-assigned on the pool itself):
// The session pool resource pulls its container image during the create
// operation. With a system-assigned identity the pull happens before any
// role assignment can be applied (the principalId only exists after the
// pool is created, and the AcrPull role assignment is then queued AFTER
// the parent — but the parent has already failed the pull and timed out).
// Pre-granting a UAMI breaks the chicken-and-egg: the identity + role
// exist BEFORE the pool starts pulling.
//
// Failure mode this fixes: `SessionPoolOperationError: ... pool group
// create/update failed with error: time out.` See
// .squad/skills/aca-provision-recovery/SKILL.md (session pool variant).

@description('Name for the user-assigned managed identity')
param name string

@description('Location (resource group region)')
param location string

@description('ACR resource ID — AcrPull scope')
param acrId string

// Built-in role: AcrPull
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

// Deterministic guid() name — see aca-provision-recovery SKILL for the
// random-vs-deterministic collision rationale.
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, uami.id, acrPullRoleId)
  scope: acr
  properties: {
    principalId: uami.properties.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalType: 'ServicePrincipal'
  }
}

output id string = uami.id
output principalId string = uami.properties.principalId
output clientId string = uami.properties.clientId
