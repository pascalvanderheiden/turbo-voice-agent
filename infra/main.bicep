targetScope = 'subscription'

@description('Primary location for most resources')
param location string = 'eastus2'

@description('Resource group name')
param resourceGroupName string = 'rg-turbo-voice-agent'

@description('Unique suffix for globally unique resource names')
param resourceToken string = uniqueString(subscription().id, resourceGroupName)

@description('Cosmos DB provisioned throughput per container (RU/s)')
param cosmosDbThroughput int = 400

@description('Entra ID tenant ID for authentication')
param entraTenantId string = ''

@description('Entra ID application (client) ID')
param entraClientId string = ''

@secure()
@description('Entra ID client secret for OAuth flows (Microsoft To-Do)')
param entraClientSecret string = ''

@description('Custom domain name for the frontend (e.g. voice.turboagent.nl)')
param customDomainName string = ''

@description('Existing managed certificate name to reuse (avoids duplicate cert errors)')
param existingCertName string = ''

@description('Principal ID of the deployer user for RBAC assignments (Cosmos + Storage data access)')
param deployerPrincipalId string = ''

@description('Deploy RBAC role assignments (requires User Access Administrator or Owner role)')
param deployRbac bool = true

// ──────────────────────────────────────────────
// Resource Group
// ──────────────────────────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

// ──────────────────────────────────────────────
// Container Registry
// ──────────────────────────────────────────────
module acr 'modules/container-registry.bicep' = {
  name: 'acr'
  scope: rg
  params: {
    name: 'acr${resourceToken}'
    location: location
  }
}

// ──────────────────────────────────────────────
// Azure Cosmos DB
// ──────────────────────────────────────────────
module cosmos 'modules/cosmos-db.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    name: 'cosmos-${resourceToken}'
    location: location
    throughput: cosmosDbThroughput
  }
}

// ──────────────────────────────────────────────
// Storage (Azure Files for persistent data)
// ──────────────────────────────────────────────
module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: 'st${resourceToken}'
    location: location
  }
}

// ──────────────────────────────────────────────
// AI Foundry — East US 2
// ──────────────────────────────────────────────
module aiEastUs2 'modules/ai-foundry-eastus2.bicep' = {
  name: 'ai-eastus2'
  scope: rg
  params: {
    name: 'ai-eastus2-${resourceToken}'
    location: 'eastus2'
  }
}

// ──────────────────────────────────────────────
// AI Foundry — West US
// ──────────────────────────────────────────────
module aiWestUs 'modules/ai-foundry-westus.bicep' = {
  name: 'ai-westus'
  scope: rg
  params: {
    name: 'ai-westus-${resourceToken}'
    location: 'westus'
  }
}

// ──────────────────────────────────────────────
// AI Foundry — Central US (gpt-realtime)
// ──────────────────────────────────────────────
module aiCentralUs 'modules/ai-foundry-centralus.bicep' = {
  name: 'ai-centralus'
  scope: rg
  params: {
    name: 'ai-centralus-${resourceToken}'
    location: 'centralus'
  }
}

// ──────────────────────────────────────────────
// Container Apps Environment
// ──────────────────────────────────────────────
module cae 'modules/container-apps-env.bicep' = {
  name: 'cae'
  scope: rg
  params: {
    name: 'cae-${resourceToken}'
    location: location
  }
}

// ──────────────────────────────────────────────
// Container App — Backend
// ──────────────────────────────────────────────
module backend 'modules/container-app-backend.bicep' = {
  name: 'deploy-ca-backend'
  scope: rg
  params: {
    name: 'ca-backend-${resourceToken}'
    location: location
    containerAppsEnvId: cae.outputs.id
    acrLoginServer: acr.outputs.loginServer
    cosmosEndpoint: cosmos.outputs.endpoint
    aiEastUs2Endpoint: aiEastUs2.outputs.endpoint
    aiWestUsEndpoint: aiWestUs.outputs.endpoint
    aiCentralUsEndpoint: aiCentralUs.outputs.endpoint
    storageAccountName: storage.outputs.name
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    entraClientSecret: entraClientSecret
    todoOAuthRedirectUri: customDomainName != '' ? 'https://${customDomainName}/api/auth/callback/microsoft-todo' : 'https://ca-backend-${resourceToken}.${cae.outputs.defaultDomain}/api/auth/callback/microsoft-todo'
    frontendUrl: customDomainName != '' ? 'https://${customDomainName}' : 'https://ca-frontend-${resourceToken}.${cae.outputs.defaultDomain}'
    allowedOrigins: customDomainName != '' ? 'https://${customDomainName},https://ca-frontend-${resourceToken}.${cae.outputs.defaultDomain}' : 'https://ca-frontend-${resourceToken}.${cae.outputs.defaultDomain}'
    sandboxFqdn: 'ca-sandbox-${resourceToken}.internal.${cae.outputs.defaultDomain}'
  }
}

// ──────────────────────────────────────────────
// Container App — Sandbox (GitHub Copilot CLI)
// ──────────────────────────────────────────────
module sandbox 'modules/container-app-sandbox.bicep' = {
  name: 'deploy-ca-sandbox'
  scope: rg
  params: {
    name: 'ca-sandbox-${resourceToken}'
    location: location
    containerAppsEnvId: cae.outputs.id
    backendFqdn: backend.outputs.fqdn
    storageAccountName: storage.outputs.name
  }
}

// ──────────────────────────────────────────────
// Container App — Frontend
// ──────────────────────────────────────────────
module frontend 'modules/container-app-frontend.bicep' = {
  name: 'deploy-ca-frontend'
  scope: rg
  params: {
    name: 'ca-frontend-${resourceToken}'
    location: location
    containerAppsEnvId: cae.outputs.id
    acrLoginServer: acr.outputs.loginServer
    backendFqdn: backend.outputs.fqdn
    customDomainName: customDomainName
    existingCertName: existingCertName
    entraTenantId: entraTenantId
    entraClientId: entraClientId
  }
}

// ──────────────────────────────────────────────
// RBAC Role Assignments
// ──────────────────────────────────────────────
module rbac 'modules/rbac.bicep' = if (deployRbac) {
  name: 'rbac'
  scope: rg
  params: {
    backendPrincipalId: backend.outputs.principalId
    frontendPrincipalId: frontend.outputs.principalId
    cosmosAccountName: cosmos.outputs.name
    acrName: acr.outputs.name
    storageAccountName: storage.outputs.name
    aiEastUs2Name: aiEastUs2.outputs.name
    aiWestUsName: aiWestUs.outputs.name
    aiCentralUsName: aiCentralUs.outputs.name
    sandboxPrincipalId: sandbox.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY string = acr.outputs.loginServer
output BACKEND_URL string = 'https://${backend.outputs.fqdn}'
output FRONTEND_URL string = 'https://${frontend.outputs.fqdn}'
output COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AI_EASTUS2_ENDPOINT string = aiEastUs2.outputs.endpoint
output AI_WESTUS_ENDPOINT string = aiWestUs.outputs.endpoint
output AI_CENTRALUS_ENDPOINT string = aiCentralUs.outputs.endpoint
output SANDBOX_URL string = 'https://${sandbox.outputs.fqdn}'
