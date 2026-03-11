@description('AI Foundry account name')
param name string

@description('Location')
param location string = 'westus'

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
    defaultProject: 'default-westus'
    associatedProjects: [
      'default-westus'
    ]
  }
}

// ──────────────────────────────────────────────
// Default Project
// ──────────────────────────────────────────────
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: 'default-westus'
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Default project created with the resource'
    displayName: 'default-westus'
  }
}

// ──────────────────────────────────────────────
// Model Deployments
// ──────────────────────────────────────────────
resource o3DeepResearch 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'o3-deep-research'
  sku: {
    name: 'GlobalStandard'
    capacity: 1500
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'o3-deep-research'
      version: '2025-06-26'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [project]
}

output endpoint string = account.properties.endpoint
output name string = account.name
output id string = account.id
