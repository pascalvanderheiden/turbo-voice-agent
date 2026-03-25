// aci-network.bicep — Standalone VNet for ACI sandbox containers.
// Separate from the CAE managed VNet to avoid modifying the existing environment.
// The backend Container App accesses ACI via private IPs through VNet peering
// or service endpoints.

@description('VNet name')
param name string

@description('Location')
param location string

// ── NSG: only allow port 3000 inbound ──
resource nsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${name}'
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
          destinationAddressPrefix: '10.1.0.0/24'
          destinationPortRange: '3000'
        }
      }
      {
        name: 'DenyAllOtherInbound'
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

// ── VNet with a single ACI-delegated subnet ──
resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: name
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.1.0.0/16']
    }
    subnets: [
      {
        name: 'snet-aci-sandbox'
        properties: {
          addressPrefix: '10.1.0.0/24'
          delegations: [
            {
              name: 'aci-delegation'
              properties: {
                serviceName: 'Microsoft.ContainerInstance/containerGroups'
              }
            }
          ]
          networkSecurityGroup: { id: nsg.id }
        }
      }
    ]
  }
}

output subnetId string = vnet.properties.subnets[0].id
output vnetId string = vnet.id
