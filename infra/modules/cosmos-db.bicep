@description('Cosmos DB account name')
param name string

@description('Location')
param location string

@description('Provisioned throughput per container (RU/s)')
param throughput int = 400

var databaseName = 'turbovoice'
var containers = ['notes', 'ideas', 'research', 'specs', 'dev_tasks', 'marketing', 'skills', 'profiles']

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: name
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    backupPolicy: {
      type: 'Continuous'
      continuousModeProperties: {
        tier: 'Continuous7Days'
      }
    }
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

@batchSize(1)
resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [
  for c in containers: {
    parent: database
    name: c
    properties: {
      resource: {
        id: c
        partitionKey: {
          paths: ['/userId']
          kind: 'Hash'
        }
      }
      options: {
        throughput: throughput
      }
    }
  }
]

output endpoint string = account.properties.documentEndpoint
output name string = account.name
output id string = account.id
