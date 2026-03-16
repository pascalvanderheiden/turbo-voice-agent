@description('Backend Container App managed identity principal ID')
param backendPrincipalId string

@description('Frontend Container App managed identity principal ID')
param frontendPrincipalId string

@description('Cosmos DB account name')
param cosmosAccountName string

@description('ACR name')
param acrName string

@description('Storage account name')
param storageAccountName string

@description('AI Foundry East US 2 account name')
param aiEastUs2Name string

@description('AI Foundry West US account name')
param aiWestUsName string

@description('AI Foundry Central US account name')
param aiCentralUsName string

@description('Sandbox Container App managed identity principal ID')
param sandboxPrincipalId string = ''

@description('Principal ID of the deployer user for data access (optional)')
param deployerPrincipalId string = ''

// Built-in role definition IDs
var cosmosDataContributor = '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
var cognitiveServicesOpenAIUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageFileDataContributor = '0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb'
var acrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

// Existing resources
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource aiEastUs2 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiEastUs2Name
}

resource aiWestUs 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiWestUsName
}

resource aiCentralUs 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiCentralUsName
}

// ──────────────────────────────────────────────
// Cosmos DB — Backend
// ──────────────────────────────────────────────
resource cosmosRbac 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, backendPrincipalId, cosmosDataContributor)
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributor}'
    scope: cosmosAccount.id
  }
}

// ──────────────────────────────────────────────
// AI Foundry East US 2 — Backend
// ──────────────────────────────────────────────
resource aiEastUs2Rbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiEastUs2.id, backendPrincipalId, cognitiveServicesOpenAIUser)
  scope: aiEastUs2
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// AI Foundry West US — Backend
// ──────────────────────────────────────────────
resource aiWestUsRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiWestUs.id, backendPrincipalId, cognitiveServicesOpenAIUser)
  scope: aiWestUs
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// AI Foundry Central US — Backend
// ──────────────────────────────────────────────
resource aiCentralUsRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiCentralUs.id, backendPrincipalId, cognitiveServicesOpenAIUser)
  scope: aiCentralUs
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// Storage — Backend (Blob Data Contributor for skills)
// ──────────────────────────────────────────────
resource storageBlobRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, backendPrincipalId, storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// Storage — Backend (File Data Contributor)
// ──────────────────────────────────────────────
resource storageRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, backendPrincipalId, storageFileDataContributor)
  scope: storageAccount
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageFileDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// ACR Pull — Backend
// ──────────────────────────────────────────────
resource acrBackendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, backendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: backendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// ACR Pull — Frontend
// ──────────────────────────────────────────────
resource acrFrontendRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, frontendPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: frontendPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// ACR Pull — Sandbox
// ──────────────────────────────────────────────
resource acrSandboxRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(sandboxPrincipalId)) {
  name: guid(acr.id, sandboxPrincipalId, acrPull)
  scope: acr
  properties: {
    principalId: sandboxPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// Storage Blob Data Reader — Sandbox (for skill sync from Blob Storage)
// ──────────────────────────────────────────────
var storageBlobDataReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
resource sandboxBlobReaderRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(sandboxPrincipalId)) {
  name: guid(storageAccount.id, sandboxPrincipalId, storageBlobDataReader)
  scope: storageAccount
  properties: {
    principalId: sandboxPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataReader)
    principalType: 'ServicePrincipal'
  }
}

// ──────────────────────────────────────────────
// Deployer — Cosmos DB Data Contributor (for debugging/admin access)
// ──────────────────────────────────────────────
resource deployerCosmosRbac 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = if (!empty(deployerPrincipalId)) {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, deployerPrincipalId, cosmosDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributor}'
    scope: cosmosAccount.id
  }
}

// ──────────────────────────────────────────────
// Deployer — Storage Blob Data Contributor (for debugging/admin access)
// ──────────────────────────────────────────────
resource deployerStorageBlobRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId)) {
  name: guid(storageAccount.id, deployerPrincipalId, storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
    principalType: 'User'
  }
}
