// vnet-cae.bicep — VNet for Container Apps Environment and private endpoints.

@description('VNet name')
param name string

@description('Location')
param location string

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: name
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.2.0.0/16']
    }
    subnets: [
      {
        name: 'snet-cae-infra'
        properties: {
          addressPrefix: '10.2.0.0/23'
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.2.2.0/24'
        }
      }
      {
        name: 'snet-reserved'
        properties: {
          addressPrefix: '10.2.3.0/24'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output infraSubnetId string = vnet.properties.subnets[0].id
output privateEndpointsSubnetId string = vnet.properties.subnets[1].id
