@description('AI Foundry account name')
param name string

@description('Location')
param location string = 'eastus2'

// ──────────────────────────────────────────────
// AI Services Account with Project Management
// ──────────────────────────────────────────────
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  kind: 'AIServices'
  tags: {
    SecurityControl: 'Ignore'
  }
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
    defaultProject: 'default-eastus2'
    associatedProjects: [
      'default-eastus2'
    ]
  }
}

// ──────────────────────────────────────────────
// Default Project
// ──────────────────────────────────────────────
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: 'default-eastus2'
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Default project created with the resource'
    displayName: 'default-eastus2'
  }
}

// ──────────────────────────────────────────────
// Model Deployments (sequential to avoid conflicts)
// ──────────────────────────────────────────────
resource gpt52 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'gpt-5.2'
  sku: {
    name: 'GlobalStandard'
    capacity: 500
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.2'
      version: '2025-12-11'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [project]
}

resource gpt41 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'gpt-4.1'
  sku: {
    name: 'GlobalStandard'
    capacity: 500
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt52]
}

resource gpt4oTranscribe 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'gpt-4o-transcribe'
  sku: {
    name: 'GlobalStandard'
    capacity: 200
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-transcribe'
      version: '2025-03-20'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt41]
}

// sora-2 deployed manually — commenting out to avoid quota conflicts
// resource sora2 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
//   parent: account
//   name: 'sora-2'
//   sku: {
//     name: 'GlobalStandard'
//     capacity: 50
//   }
//   properties: {
//     model: {
//       format: 'OpenAI'
//       name: 'sora-2'
//       version: '2025-10-06'
//     }
//     versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
//     raiPolicyName: 'Microsoft.DefaultV2'
//   }
//   dependsOn: [gpt4oTranscribe]
// }

output endpoint string = account.properties.endpoint
output name string = account.name
output id string = account.id
