// aci-identity.bicep — User-assigned managed identity shared by all ACI sandbox containers.
// Grants AcrPull on the container registry and Storage Blob Data Reader on the skills
// storage account so ACI containers can pull images and sync skills at startup.

@description('Identity name')
param name string

@description('Location')
param location string

@description('Container Registry resource ID')
param acrId string

@description('Storage Account resource ID')
param storageAccountId string

// Well-known role definition IDs
var acrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var storageBlobDataReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

// ACR Pull — allows ACI to pull the sandbox Docker image
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, identity.id, acrPull)
  scope: acr
  properties: {
    principalId: identity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Reader — allows ACI to download skills from blob storage
resource blobReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountId, identity.id, storageBlobDataReader)
  scope: storageAccount
  properties: {
    principalId: identity.properties.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataReader
    )
    principalType: 'ServicePrincipal'
  }
}

// Reference existing resources for scoping role assignments
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: last(split(storageAccountId, '/'))
}

output id string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
