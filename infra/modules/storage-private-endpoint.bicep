// storage-private-endpoint.bicep — Private endpoints + DNS for Azure Storage (blob + file).

@description('Base name for private endpoint resources')
param name string

@description('Location')
param location string

@description('Storage account resource ID')
param storageAccountId string

@description('Storage account name')
param storageAccountName string

@description('Subnet ID for the private endpoints')
param subnetId string

@description('VNet ID to link the private DNS zones to')
param vnetId string

// ──────────────────────────────────────────────
// Blob Private Endpoint
// ──────────────────────────────────────────────
resource blobEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: '${name}-blob'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${name}-blob'
        properties: {
          privateLinkServiceId: storageAccountId
          groupIds: ['blob']
        }
      }
    ]
  }
}

resource blobDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
}

resource blobVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: blobDnsZone
  name: '${storageAccountName}-blob-vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnetId
    }
    registrationEnabled: false
  }
}

resource blobDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: blobEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob-dns-config'
        properties: {
          privateDnsZoneId: blobDnsZone.id
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────
// File Private Endpoint
// ──────────────────────────────────────────────
resource fileEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: '${name}-file'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${name}-file'
        properties: {
          privateLinkServiceId: storageAccountId
          groupIds: ['file']
        }
      }
    ]
  }
}

resource fileDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.file.core.windows.net'
  location: 'global'
}

resource fileVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: fileDnsZone
  name: '${storageAccountName}-file-vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnetId
    }
    registrationEnabled: false
  }
}

resource fileDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: fileEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'file-dns-config'
        properties: {
          privateDnsZoneId: fileDnsZone.id
        }
      }
    ]
  }
}
