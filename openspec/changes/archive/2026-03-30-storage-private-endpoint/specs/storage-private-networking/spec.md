## ADDED Requirements

### Requirement: Private endpoints for Storage Account
The system SHALL create private endpoints for the storage account targeting `blob` and `file` sub-resources on the `snet-private-endpoints` subnet.

#### Scenario: Blob private endpoint provisioned
- **WHEN** `azd up` is executed
- **THEN** a private endpoint named `pe-st-blob-{env}` SHALL be created in the `snet-private-endpoints` subnet targeting the storage account's `blob` sub-resource

#### Scenario: File private endpoint provisioned
- **WHEN** `azd up` is executed
- **THEN** a private endpoint named `pe-st-file-{env}` SHALL be created in the `snet-private-endpoints` subnet targeting the storage account's `file` sub-resource

#### Scenario: Private endpoint connections approved
- **WHEN** the private endpoints are created
- **THEN** both private endpoint connection statuses SHALL be `Approved` on the storage account

### Requirement: Private DNS zones for Storage Account
The system SHALL create private DNS zones for blob and file services, linked to the CAE VNet, so that storage endpoints resolve to private IPs.

#### Scenario: Blob DNS zone created and linked
- **WHEN** `azd up` is executed
- **THEN** a private DNS zone `privatelink.blob.core.windows.net` SHALL be created and linked to the CAE VNet

#### Scenario: File DNS zone created and linked
- **WHEN** `azd up` is executed
- **THEN** a private DNS zone `privatelink.file.core.windows.net` SHALL be created and linked to the CAE VNet

#### Scenario: DNS A-records auto-registered
- **WHEN** the private endpoints are created with DNS zone group integration
- **THEN** A-records SHALL be automatically created in each respective DNS zone mapping the storage account hostname to the private endpoint IPs

### Requirement: Storage network ACLs deny public access
The system SHALL set the storage account `networkAcls.defaultAction` to `Deny` to comply with Azure Policy, while maintaining `bypass: 'AzureServices'`.

#### Scenario: Public access denied
- **WHEN** private endpoints are active and DNS resolution confirmed
- **THEN** the storage account SHALL have `networkAcls.defaultAction` set to `Deny`

#### Scenario: Azure service bypass preserved
- **WHEN** public access is denied
- **THEN** the `networkAcls.bypass` SHALL remain set to `AzureServices`

#### Scenario: Shared key access preserved
- **WHEN** network ACLs are updated
- **THEN** `allowSharedKeyAccess` SHALL remain `true` for Azure Files CIFS/SMB mount compatibility

### Requirement: Azure Files mount continues working via private endpoint
The system SHALL ensure the Azure Files share `turbodata` remains accessible from Container Apps through the file private endpoint using shared key authentication over SMB.

#### Scenario: File share accessible after private endpoint cutover
- **WHEN** public access is denied and the file private endpoint is active
- **THEN** the Container Apps volume mount for the `turbodata` file share SHALL continue to function

#### Scenario: Storage key output preserved
- **WHEN** the storage module is deployed with private endpoints
- **THEN** the `key` output from `storage.bicep` SHALL continue to return a valid storage account key for volume mount configuration

### Requirement: Existing data preserved
The system SHALL ensure all existing storage data remains intact throughout the network access change.

#### Scenario: Blob containers preserved
- **WHEN** network ACLs are changed and private endpoints are added
- **THEN** all blob containers (`skills`, `uploads`, `marketing-videos`, `openspec-imports`) and their contents SHALL remain intact

#### Scenario: File share preserved
- **WHEN** network ACLs are changed and private endpoints are added
- **THEN** the `turbodata` file share and its contents SHALL remain intact
