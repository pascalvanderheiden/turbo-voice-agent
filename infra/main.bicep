targetScope = 'subscription'

@description('Primary location for most resources')
param location string = 'eastus2'

@description('Resource group name')
param resourceGroupName string = 'rg-turbo-voice-agent'

@description('Azure Developer CLI environment name')
param azdEnvironmentName string = ''

@description('Unique suffix for globally unique resource names')
param resourceToken string = uniqueString(subscription().id, resourceGroupName)

@description('Cosmos DB provisioned throughput per container (RU/s)')
param cosmosDbThroughput int = 400

@description('Azure region for Primary AI Foundry (gpt-5.2, gpt-4.1, gpt-4o-transcribe)')
param primaryAiLocation string = 'eastus2'

@description('Azure region for Voice AI Foundry (gpt-realtime)')
param voiceAiLocation string = 'centralus'

@description('Azure region for Research AI Foundry (o3-deep-research)')
param researchAiLocation string = 'westus'

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
// Session Pool parameters (custom-container dynamic sessions)
// ──────────────────────────────────────────────
@description('Maximum number of concurrent sessions the sandbox pool will allocate')
param sessionPoolMaxConcurrent int = 30

@description('Number of prewarmed/ready session instances kept in the pool at all times')
param sessionPoolReadyInstances int = 1

@description('Cooldown period in seconds before an idle session is destroyed')
param sessionPoolCooldownSeconds int = 300

@description('CPU cores per session container')
param sessionPoolCpu string = '1.0'

@description('Memory per session container (e.g. 2Gi, 4Gi)')
param sessionPoolMemory string = '2Gi'

@description('Sandbox image tag in ACR (defaults to :latest)')
param sandboxImageTag string = 'latest'

// ──────────────────────────────────────────────
// Resource Group
// ──────────────────────────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: union(
    {
      'azd-template': 'turbo-voice-agent'
    },
    azdEnvironmentName != '' ? {
      'azd-env-name': azdEnvironmentName
    } : {}
  )
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
    location: primaryAiLocation
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
    location: researchAiLocation
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
    location: voiceAiLocation
  }
}

// ──────────────────────────────────────────────
// VNet for Container Apps + Private Endpoints
// ──────────────────────────────────────────────
module vnetCae 'modules/vnet-cae.bicep' = {
  name: 'vnet-cae'
  scope: rg
  params: {
    name: 'vnet-cae-${resourceToken}'
    location: location
  }
}

// ──────────────────────────────────────────────
// Cosmos DB Private Endpoint + DNS
// ──────────────────────────────────────────────
module cosmosPrivateEndpoint 'modules/cosmos-private-endpoint.bicep' = {
  name: 'cosmos-private-endpoint'
  scope: rg
  params: {
    name: 'pe-cosmos-${resourceToken}'
    location: location
    cosmosAccountId: cosmos.outputs.id
    cosmosAccountName: cosmos.outputs.name
    subnetId: vnetCae.outputs.privateEndpointsSubnetId
    vnetId: vnetCae.outputs.vnetId
  }
}

// ──────────────────────────────────────────────
// Storage Private Endpoints + DNS (blob + file)
// ──────────────────────────────────────────────
module storagePrivateEndpoint 'modules/storage-private-endpoint.bicep' = {
  name: 'storage-private-endpoint'
  scope: rg
  params: {
    name: 'pe-st-${resourceToken}'
    location: location
    storageAccountId: storage.outputs.id
    storageAccountName: storage.outputs.name
    subnetId: vnetCae.outputs.privateEndpointsSubnetId
    vnetId: vnetCae.outputs.vnetId
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
    infrastructureSubnetId: vnetCae.outputs.infraSubnetId
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
    sessionPoolManagementEndpoint: sessionPool.outputs.sessionPoolManagementEndpoint
    sessionPoolName: sessionPool.outputs.sessionPoolName
  }
}

// ──────────────────────────────────────────────
// Sandbox — Container Apps Dynamic Session Pool
// Replaces the deleted ACI per-task containers and shared `ca-sandbox-*`
// Container App. The pool pulls the existing sandbox image from ACR using
// its own system-assigned managed identity (AcrPull role assignment is
// created inside session-pool.bicep with a deterministic guid() name).
//
// NOTE: backendFqdn is computed from the predictable CAE-default-domain
// pattern rather than backend.outputs.fqdn to avoid a Bicep cycle
// (backend module also reads sessionPool outputs for env vars).
// ──────────────────────────────────────────────
var backendFqdnComputed = customDomainName != '' ? customDomainName : 'ca-backend-${resourceToken}.${cae.outputs.defaultDomain}'

// ── UAMI for the session pool image pull, AcrPull pre-granted ──
// MUST be deployed BEFORE the sessionPool module so the role assignment
// exists when the pool tries to pull. Removing this step reintroduces the
// "pool group create/update failed with error: time out" failure mode.
module sessionPoolIdentity 'modules/session-pool-identity.bicep' = {
  name: 'session-pool-identity'
  scope: rg
  params: {
    name: 'id-sandbox-pool-${resourceToken}'
    location: location
    acrId: acr.outputs.id
  }
}

module sessionPool 'modules/session-pool.bicep' = {
  name: 'deploy-session-pool'
  scope: rg
  params: {
    name: 'sp-sandbox-${resourceToken}'
    location: location
    containerAppsEnvId: cae.outputs.id
    image: '${acr.outputs.loginServer}/turbo-voice-agent/sandbox:${sandboxImageTag}'
    acrLoginServer: acr.outputs.loginServer
    pullIdentityId: sessionPoolIdentity.outputs.id
    backendFqdn: backendFqdnComputed
    storageAccountName: storage.outputs.name
    maxConcurrentSessions: sessionPoolMaxConcurrent
    readySessionInstances: sessionPoolReadyInstances
    cooldownPeriodInSeconds: sessionPoolCooldownSeconds
    cpu: sessionPoolCpu
    memory: sessionPoolMemory
  }
}

// ──────────────────────────────────────────────
// RBAC — Backend identity → Session Pool (Azure ContainerApps Session Executor)
// Deterministic guid() name — never use random GUIDs here (see
// .squad/skills/aca-provision-recovery/SKILL.md collision pattern).
// ──────────────────────────────────────────────
module sessionPoolRole 'modules/session-pool-role.bicep' = if (deployRbac) {
  name: 'session-pool-role'
  scope: rg
  params: {
    sessionPoolName: sessionPool.outputs.name
    principalId: backend.outputs.principalId
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
    deployerPrincipalId: deployerPrincipalId
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY string = acr.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.outputs.loginServer
output BACKEND_URL string = 'https://${backend.outputs.fqdn}'
output FRONTEND_URL string = customDomainName != '' ? 'https://${customDomainName}' : 'https://${frontend.outputs.fqdn}'
output COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AI_EASTUS2_ENDPOINT string = aiEastUs2.outputs.endpoint
output AI_WESTUS_ENDPOINT string = aiWestUs.outputs.endpoint
output AI_CENTRALUS_ENDPOINT string = aiCentralUs.outputs.endpoint
output SESSION_POOL_MANAGEMENT_ENDPOINT string = sessionPool.outputs.sessionPoolManagementEndpoint
output SESSION_POOL_NAME string = sessionPool.outputs.sessionPoolName
