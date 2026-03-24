@description('Container Apps Environment name')
param name string

@description('Location')
param location string

@description('Deploy VNet with ACI subnet for per-task sandbox isolation')
param enableAciSubnet bool = false

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${name}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ── Standalone VNet for ACI sandbox (does NOT change CAE networking) ──
resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = if (enableAciSubnet) {
  name: 'vnet-${name}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'snet-aci-sandbox'
        properties: {
          addressPrefix: '10.0.4.0/24'
          delegations: [
            {
              name: 'aci-delegation'
              properties: {
                serviceName: 'Microsoft.ContainerInstance/containerGroups'
              }
            }
          ]
          networkSecurityGroup: enableAciSubnet ? { id: aciNsg.id } : null
        }
      }
    ]
  }
}

// ── NSG for ACI subnet — restrict inbound to port 3000 ──
resource aciNsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = if (enableAciSubnet) {
  name: 'nsg-aci-sandbox-${name}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowSandboxPort'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '10.0.4.0/24'
          destinationPortRange: '3000'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

// CAE keeps its managed VNet — no vnetConfiguration change
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

output id string = cae.id
output name string = cae.name
output defaultDomain string = cae.properties.defaultDomain
output aciSubnetId string = enableAciSubnet ? vnet.properties.subnets[0].id : ''
