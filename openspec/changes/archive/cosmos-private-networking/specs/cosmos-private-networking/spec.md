## ADDED Requirements

### Requirement: VNet for Container Apps Environment
The system SHALL provision a Virtual Network (`vnet-cae`) with address space `10.2.0.0/16` containing dedicated subnets for Container Apps infrastructure and private endpoints.

#### Scenario: VNet provisioned with correct subnets
- **WHEN** `azd up` is executed
- **THEN** a VNet named `vnet-cae-{env}` SHALL be created with subnets `snet-cae-infra` (`10.2.0.0/23`), `snet-private-endpoints` (`10.2.2.0/24`), and `snet-reserved` (`10.2.3.0/24`)

#### Scenario: CAE infrastructure subnet sizing
- **WHEN** the `snet-cae-infra` subnet is provisioned
- **THEN** it SHALL use a `/23` CIDR block minimum as required by Azure Container Apps Environment VNet integration

### Requirement: Private endpoint for Cosmos DB
The system SHALL create a private endpoint connecting the Cosmos DB account to the `snet-private-endpoints` subnet, targeting the `Sql` sub-resource group.

#### Scenario: Private endpoint provisioned
- **WHEN** `azd up` is executed
- **THEN** a private endpoint named `pe-cosmos-{env}` SHALL be created in the `snet-private-endpoints` subnet targeting the existing Cosmos DB account's `Sql` sub-resource

#### Scenario: Private endpoint connection approved
- **WHEN** the private endpoint is created
- **THEN** the private endpoint connection status SHALL be `Approved` on the Cosmos DB account

### Requirement: Private DNS zone for Cosmos DB
The system SHALL create a private DNS zone `privatelink.documents.azure.com` linked to the CAE VNet so that the Cosmos DB endpoint resolves to the private IP.

#### Scenario: DNS zone created and linked
- **WHEN** `azd up` is executed
- **THEN** a private DNS zone `privatelink.documents.azure.com` SHALL be created and linked to the `vnet-cae-{env}` VNet

#### Scenario: DNS resolution returns private IP
- **WHEN** the backend Container App resolves the Cosmos DB endpoint hostname
- **THEN** the DNS response SHALL return the private endpoint's IP address (in the `10.2.2.0/24` range) instead of the public IP

#### Scenario: DNS A-record auto-registered
- **WHEN** the private endpoint is created with DNS zone group integration
- **THEN** an A-record SHALL be automatically created in the private DNS zone mapping the Cosmos DB account hostname to the private endpoint IP

### Requirement: Container Apps Environment VNet integration
The system SHALL configure the Container Apps Environment with VNet integration using the `snet-cae-infra` subnet while maintaining external ingress.

#### Scenario: CAE deployed with VNet integration
- **WHEN** `azd up` is executed
- **THEN** the Container Apps Environment SHALL be configured with `vnetConfiguration.infrastructureSubnetId` set to the `snet-cae-infra` subnet and `vnetConfiguration.internal` set to `false`

#### Scenario: External ingress preserved
- **WHEN** the CAE is configured with VNet integration
- **THEN** the frontend and backend Container Apps SHALL remain accessible via their public URLs and custom domains

### Requirement: Cosmos DB public network access disabled
The system SHALL set Cosmos DB `publicNetworkAccess` to `Disabled` to comply with Azure Policy.

#### Scenario: Public access disabled after private endpoint is active
- **WHEN** the private endpoint is provisioned and DNS resolution is confirmed working
- **THEN** the Cosmos DB account SHALL have `publicNetworkAccess` set to `Disabled`

#### Scenario: Existing data preserved
- **WHEN** public network access is disabled
- **THEN** all existing databases, containers, and documents in Cosmos DB SHALL remain intact and accessible via the private endpoint

### Requirement: VNet peering with ACI sandbox VNet
The system SHALL establish bidirectional VNet peering between the CAE VNet (`10.2.0.0/16`) and the ACI sandbox VNet (`10.1.0.0/16`).

#### Scenario: Bidirectional peering established
- **WHEN** `azd up` is executed
- **THEN** VNet peering SHALL be created in both directions: CAE VNet → ACI VNet and ACI VNet → CAE VNet, with `allowVirtualNetworkAccess` set to `true`

#### Scenario: No address space overlap
- **WHEN** the peering is configured
- **THEN** the two VNet address spaces (`10.1.0.0/16` and `10.2.0.0/16`) SHALL not overlap
