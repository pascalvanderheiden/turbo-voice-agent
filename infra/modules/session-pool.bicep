// session-pool.bicep — Azure Container Apps dynamic session pool (custom container).
// Replaces the dual ACI + shared Container App sandbox runtime. Sessions are
// prewarmed, allocated by caller-provided `identifier`, and pulled from ACR
// via the pool's system-assigned managed identity.

@description('Session pool resource name')
param name string

@description('Location (must match the Container Apps Environment)')
param location string

@description('Container Apps Environment resource ID')
param containerAppsEnvId string

@description('Fully qualified container image reference (e.g. acr.azurecr.io/turbo-voice-agent/sandbox:latest)')
param image string

@description('ACR login server (used in registryCredentials)')
param acrLoginServer string

@description('ACR resource ID (used to scope the AcrPull role assignment for the pool identity)')
param acrId string

@description('Backend container app FQDN, used to set BACKEND_URL inside session containers')
param backendFqdn string = ''

@description('Storage account name for skills sync inside the session container')
param storageAccountName string = ''

@description('Default Copilot CLI model used inside the session container')
param copilotModel string = 'claude-opus-4.6'

@description('Target port the session container listens on (matches sandbox HTTP server)')
param targetPort int = 3000

@description('Maximum number of concurrent sessions the pool will allocate')
param maxConcurrentSessions int = 30

@description('Number of prewarmed/ready session instances to keep at all times')
param readySessionInstances int = 1

@description('Cooldown period (seconds) before an idle session is destroyed by the pool')
param cooldownPeriodInSeconds int = 300

@description('CPU cores per session container (e.g. 1.0, 2.0)')
param cpu string = '1.0'

@description('Memory per session container (e.g. 2Gi, 4Gi)')
param memory string = '2Gi'

// Built-in role definition: AcrPull
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource sessionPool 'Microsoft.App/sessionPools@2025-02-02-preview' = {
  name: name
  location: location
  tags: {
    'azd-service-name': 'sandbox'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerAppsEnvId
    poolManagementType: 'Dynamic'
    containerType: 'CustomContainer'
    scaleConfiguration: {
      maxConcurrentSessions: maxConcurrentSessions
      readySessionInstances: readySessionInstances
    }
    dynamicPoolConfiguration: {
      lifecycleConfiguration: {
        lifecycleType: 'Timed'
        cooldownPeriodInSeconds: cooldownPeriodInSeconds
      }
    }
    customContainerTemplate: {
      containers: [
        {
          name: 'sandbox'
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            { name: 'PORT', value: string(targetPort) }
            { name: 'BACKEND_URL', value: backendFqdn != '' ? 'https://${backendFqdn}' : '' }
            { name: 'COPILOT_MODEL', value: copilotModel }
            { name: 'AZURE_STORAGE_ACCOUNT_NAME', value: storageAccountName }
          ]
          // Probes per Design §6: liveness checks /health every 10s; startup checks
          // /ready every 5s up to 30 attempts (skills sync must finish before /ready
          // returns 200). Pool removes/replaces any instance that fails probes.
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: targetPort
                scheme: 'HTTP'
              }
              periodSeconds: 10
              initialDelaySeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Startup'
              httpGet: {
                path: '/ready'
                port: targetPort
                scheme: 'HTTP'
              }
              periodSeconds: 5
              failureThreshold: 30
            }
          ]
        }
      ]
      ingress: {
        targetPort: targetPort
      }
      registryCredentials: {
        server: acrLoginServer
        identity: 'system'
      }
    }
  }
}

// ── ACR Pull for the pool's system-assigned identity ──
// Deterministic guid() name avoids the manual-vs-bicep collision pattern
// documented in .squad/skills/aca-provision-recovery/SKILL.md.
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, sessionPool.id, acrPullRoleId)
  scope: acr
  properties: {
    principalId: sessionPool.identity.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalType: 'ServicePrincipal'
  }
}

output id string = sessionPool.id
output name string = sessionPool.name
output principalId string = sessionPool.identity.principalId
output sessionPoolManagementEndpoint string = sessionPool.properties.poolManagementEndpoint
output sessionPoolName string = sessionPool.name
