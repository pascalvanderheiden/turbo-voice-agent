@description('Container App name')
param name string

@description('Location')
param location string

@description('Container Apps Environment resource ID')
param containerAppsEnvId string

@description('ACR login server')
param acrLoginServer string

@description('Cosmos DB endpoint')
param cosmosEndpoint string

@description('AI Foundry East US 2 endpoint')
param aiEastUs2Endpoint string

@description('AI Foundry West US endpoint')
param aiWestUsEndpoint string

@description('AI Foundry Central US endpoint')
param aiCentralUsEndpoint string

@description('Storage account name for Blob Storage')
param storageAccountName string

@description('Entra ID tenant ID')
param entraTenantId string = ''

@description('Entra ID client ID')
param entraClientId string = ''

@secure()
@description('Entra ID client secret for OAuth flows')
param entraClientSecret string = ''

@description('OAuth redirect URI for Microsoft To-Do callback')
param todoOAuthRedirectUri string = ''

@description('Comma-separated allowed CORS origins')
param allowedOrigins string = ''

@description('Sandbox Container App FQDN')
param sandboxFqdn string = ''

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: {
    'azd-service-name': 'backend'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: allowedOrigins != '' ? split(allowedOrigins, ',') : ['*']
          allowedMethods: ['*']
          allowedHeaders: ['*']
          allowCredentials: allowedOrigins != '' ? true : false
        }
      }
      registries: [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ]
      secrets: [
        {
          name: 'entra-client-secret'
          value: entraClientSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
          env: [
            { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
            { name: 'COSMOS_DATABASE', value: 'turbovoice' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: aiEastUs2Endpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: 'gpt-5.2' }
            { name: 'AZURE_OPENAI_SEARCH_DEPLOYMENT', value: 'gpt-4.1' }
            { name: 'AZURE_OPENAI_WESTUS_ENDPOINT', value: aiWestUsEndpoint }
            { name: 'AZURE_OPENAI_DEEP_RESEARCH_DEPLOYMENT', value: 'o3-deep-research' }
            { name: 'VOICE_LIVE_ENDPOINT', value: aiCentralUsEndpoint }
            { name: 'VOICE_LIVE_DEPLOYMENT', value: 'gpt-realtime' }
            { name: 'VOICE_TRANSCRIBE_DEPLOYMENT', value: 'gpt-4o-transcribe' }
            { name: 'SORA_ENDPOINT', value: aiEastUs2Endpoint }
            { name: 'SORA_DEPLOYMENT', value: 'sora-2' }
            { name: 'DATA_DIR', value: '/mnt/data' }
            { name: 'AZURE_STORAGE_ACCOUNT_NAME', value: storageAccountName }
            { name: 'ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'ENTRA_CLIENT_ID', value: entraClientId }
            { name: 'ENTRA_CLIENT_SECRET', secretRef: 'entra-client-secret' }
            { name: 'TODO_OAUTH_REDIRECT_URI', value: todoOAuthRedirectUri }
            { name: 'ALLOWED_ORIGINS', value: allowedOrigins }
            { name: 'SANDBOX_URL', value: sandboxFqdn != '' ? 'https://${sandboxFqdn}' : '' }
          ]
          volumeMounts: [
            {
              volumeName: 'data'
              mountPath: '/mnt/data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'data'
          storageType: 'EmptyDir'
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = backend.properties.configuration.ingress.fqdn
output principalId string = backend.identity.principalId
output name string = backend.name
