// aci-backend-role.bicep — Grant the backend Container App's managed identity
// permission to create and delete ACI container groups in this resource group.
// Uses the built-in "Contributor" role scoped to the resource group.

@description('Backend Container App system-assigned identity principal ID')
param principalId string

// Contributor role definition ID (built-in)
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

resource aciContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, principalId, contributorRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalType: 'ServicePrincipal'
  }
}
