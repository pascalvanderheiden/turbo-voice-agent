// aci-sandbox.bicep — Reference template for per-task ACI sandbox container groups.
// ACI containers are created dynamically by the backend (azure-mgmt-containerinstance SDK).
// This module defines the user-assigned identity and configuration parameters that the
// backend needs to provision ACI instances at runtime.

@description('Location for ACI resources')
param location string

@description('User-assigned managed identity resource ID for ACI containers')
param aciIdentityId string

@description('User-assigned managed identity client ID')
param aciIdentityClientId string

@description('ACR login server (e.g., acr123.azurecr.io)')
param acrLoginServer string

@description('Sandbox Docker image name (without registry prefix)')
param sandboxImageName string = 'turbo-voice-agent/sandbox'

@description('Sandbox Docker image tag')
param sandboxImageTag string = 'latest'

@description('ACI subnet ID for VNet integration')
param aciSubnetId string

@description('Backend FQDN for API callbacks')
param backendFqdn string

@description('Default Copilot CLI model')
param copilotModel string = 'claude-opus-4.6'

@description('Azure Storage account name for skill sync')
param storageAccountName string = ''

@description('CPU cores per ACI container')
param cpu string = '2.0'

@description('Memory in GB per ACI container')
param memory string = '4'

@description('Resource group name (for backend SDK to create ACI instances)')
param resourceGroupName string = resourceGroup().name

// Output configuration that the backend needs to dynamically create ACI container groups
output aciConfig object = {
  location: location
  resourceGroupName: resourceGroupName
  aciIdentityId: aciIdentityId
  aciIdentityClientId: aciIdentityClientId
  acrLoginServer: acrLoginServer
  sandboxImage: '${acrLoginServer}/${sandboxImageName}:${sandboxImageTag}'
  aciSubnetId: aciSubnetId
  cpu: cpu
  memory: memory
  env: {
    PORT: '3000'
    BACKEND_URL: 'https://${backendFqdn}'
    COPILOT_MODEL: copilotModel
    AZURE_STORAGE_ACCOUNT_NAME: storageAccountName
    SINGLE_TASK_MODE: 'true'
  }
}
