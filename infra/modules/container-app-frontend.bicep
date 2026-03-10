@description('Container App name')
param name string

@description('Location')
param location string

@description('Container Apps Environment resource ID')
param containerAppsEnvId string

@description('ACR login server')
param acrLoginServer string

@description('Backend container app FQDN')
param backendFqdn string

@description('Custom domain name (e.g. voice.turboagent.nl). Empty = no custom domain.')
param customDomainName string = ''

@description('Existing managed certificate name to reuse. If empty, a new certificate is created.')
param existingCertName string = ''

@description('Entra ID tenant ID')
param entraTenantId string = ''

@description('Entra ID client ID')
param entraClientId string = ''

// Reference the existing managed environment for certificate provisioning
resource managedEnv 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: last(split(containerAppsEnvId, '/'))
}

// Managed TLS certificate for custom domain (requires DNS CNAME + TXT records to be in place)
resource managedCert 'Microsoft.App/managedEnvironments/managedCertificates@2024-03-01' = if (customDomainName != '' && existingCertName == '') {
  parent: managedEnv
  name: 'cert-${replace(customDomainName, '.', '-')}'
  location: location
  properties: {
    subjectName: customDomainName
    domainControlValidation: 'CNAME'
  }
}

// Reference an existing managed certificate when one already exists
resource existingCert 'Microsoft.App/managedEnvironments/managedCertificates@2024-03-01' existing = if (customDomainName != '' && existingCertName != '') {
  parent: managedEnv
  name: existingCertName
}

var certId = customDomainName != '' ? (existingCertName != '' ? existingCert.id : managedCert.id) : ''

resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: {
    'azd-service-name': 'frontend'
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
        targetPort: 3000
        transport: 'auto'
        customDomains: customDomainName != '' ? [
          {
            name: customDomainName
            certificateId: certId
            bindingType: 'SniEnabled'
          }
        ] : []
      }
      registries: [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'NEXT_PUBLIC_API_URL', value: 'https://${backendFqdn}' }
            { name: 'NEXT_PUBLIC_ENTRA_CLIENT_ID', value: entraClientId }
            { name: 'NEXT_PUBLIC_ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'NEXT_PUBLIC_ENTRA_REDIRECT_URI', value: customDomainName != '' ? 'https://${customDomainName}' : 'https://${name}.${managedEnv.properties.defaultDomain}' }
          ]
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

output fqdn string = frontend.properties.configuration.ingress.fqdn
output principalId string = frontend.identity.principalId
output name string = frontend.name
