## MODIFIED Requirements

### Requirement: Sidebar navigation includes all app sections
The sidebar navigation SHALL include a "To-Dos" item linking to `/todos` with an appropriate icon (e.g., `IconChecklist` or `IconCheckbox`), positioned after existing navigation items.

#### Scenario: Todos appears in sidebar
- **WHEN** the sidebar renders
- **THEN** a "To-Dos" navigation item SHALL appear with a checklist icon, linking to `/todos`

### Requirement: User menu provides account management
The user menu SHALL include a "Connected Accounts" section showing the Microsoft To-Do connection status and an "Authenticate Once" button to initiate the OAuth flow.

#### Scenario: User menu shows disconnected state
- **WHEN** the user opens the user menu and has NOT connected Microsoft To-Do
- **THEN** the menu SHALL display a "Connect Microsoft To-Do" button with a Microsoft icon

#### Scenario: User menu shows connected state
- **WHEN** the user opens the user menu and HAS connected Microsoft To-Do
- **THEN** the menu SHALL display "Microsoft To-Do Connected" with a green status indicator and a "Disconnect" option

#### Scenario: User initiates connection from menu
- **WHEN** the user clicks "Connect Microsoft To-Do" in the user menu
- **THEN** the system SHALL call the connection API and redirect to Microsoft OAuth consent
