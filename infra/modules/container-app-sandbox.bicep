@description('Container App name')
param name string

@description('Location')
param location string

@description('Container Apps Environment resource ID')
param containerAppsEnvId string

@description('Backend FQDN for API access')
param backendFqdn string

@description('Default Copilot CLI model')
param copilotModel string = 'claude-opus-4.6'

@description('Azure Storage account name for skill sync')
param storageAccountName string = ''

resource sandbox 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: {
    'azd-service-name': 'sandbox'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 3000
        transport: 'auto'
      }
      // Note: registries are NOT configured here because during initial creation
      // the system identity doesn't have AcrPull yet (RBAC runs after this module).
      // azd deploy will configure ACR registry auth when deploying the actual image.
    }
    template: {
      containers: [
        {
          name: 'sandbox'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
          env: [
            { name: 'PORT', value: '3000' }
            { name: 'BACKEND_URL', value: 'https://${backendFqdn}' }
            { name: 'COPILOT_MODEL', value: copilotModel }
            { name: 'AZURE_STORAGE_ACCOUNT_NAME', value: storageAccountName }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = sandbox.properties.configuration.ingress.fqdn
output principalId string = sandbox.identity.principalId
output name string = sandbox.name
