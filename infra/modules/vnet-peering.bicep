// vnet-peering.bicep — Single-direction VNet peering.

@description('Name of the local VNet (must exist in same resource group)')
param localVnetName string

@description('Resource ID of the remote VNet to peer with')
param remoteVnetId string

@description('Name for this peering connection')
param peeringName string

resource localVnet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: localVnetName
}

resource peering 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-01-01' = {
  parent: localVnet
  name: peeringName
  properties: {
    remoteVirtualNetwork: {
      id: remoteVnetId
    }
    allowVirtualNetworkAccess: true
  }
}
