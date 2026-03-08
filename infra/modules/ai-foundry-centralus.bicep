@description('AI Foundry account name')
param name string

@description('Location')
param location string = 'centralus'

// ──────────────────────────────────────────────
// AI Services Account with Project Management
// ──────────────────────────────────────────────
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
    defaultProject: 'default-centralus'
    associatedProjects: [
      'default-centralus'
    ]
  }
}

// ──────────────────────────────────────────────
// Default Project
// ──────────────────────────────────────────────
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: 'default-centralus'
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Default project created with the resource'
    displayName: 'default-centralus'
  }
}

// ──────────────────────────────────────────────
// Model Deployments
// ──────────────────────────────────────────────
resource gptRealtime 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'gpt-realtime'
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-realtime'
      version: '2025-08-28'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [project]
}

output endpoint string = account.properties.endpoint
output name string = account.name
output id string = account.id
