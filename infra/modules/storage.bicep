@description('Storage account name')
param name string

@description('Location')
param location string

var fileShareName = 'turbodata'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: true  // Required for Azure Files CIFS/SMB mounts in Container Apps
  }
}

resource fileServices 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileServices
  name: fileShareName
  properties: {
    shareQuota: 10 // GB
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource skillsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobServices
  name: 'skills'
  properties: {
    publicAccess: 'None'
  }
}

output name string = storageAccount.name
output id string = storageAccount.id
output key string = storageAccount.listKeys().keys[0].value
output fileShareName string = fileShareName
