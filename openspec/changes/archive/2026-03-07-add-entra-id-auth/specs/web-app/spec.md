# Delta Spec: web-app

## ADDED Requirements

### Requirement: Entra ID Single Sign-On
The web application SHALL authenticate users via Microsoft Entra ID using MSAL.js (auth code flow with PKCE). Only users in the turboagent.nl tenant SHALL be permitted to access the application.

#### Scenario: Unauthenticated user redirected to login
- **WHEN** an unauthenticated user navigates to any page
- **THEN** the application SHALL redirect to the Microsoft Entra ID login page
- **AND** after successful authentication the user SHALL be redirected back to the requested page

#### Scenario: Non-turboagent.nl user rejected
- **WHEN** a user from a different tenant attempts to log in
- **THEN** the Entra ID login SHALL reject the attempt because the app registration is single-tenant (turboagent.nl only)

#### Scenario: Silent token renewal
- **WHEN** the user's access token is about to expire during an active session
- **THEN** MSAL SHALL silently acquire a new token without interrupting the user

### Requirement: User Profile Menu
The site header SHALL display a user profile menu in the top-right position showing the user's profile photo, display name, language selector, and logout action.

#### Scenario: Profile menu with photo
- **WHEN** the authenticated user has a profile photo in Entra ID
- **THEN** the header SHALL display their circular profile photo that opens a dropdown on click
- **AND** the dropdown SHALL show: display name, email, language selector (en/nl), and a logout button

#### Scenario: Profile menu without photo
- **WHEN** the authenticated user has no profile photo
- **THEN** the header SHALL display a circular avatar with the user's initials

#### Scenario: Logout
- **WHEN** the user clicks logout in the profile menu
- **THEN** MSAL SHALL clear the session and redirect to the Entra ID logout endpoint
- **AND** the user SHALL be redirected back to the login page

### Requirement: User Language Preference
The user's language preference SHALL be stored in their backend profile and synchronized across devices.

#### Scenario: Change language in profile menu
- **WHEN** the user selects a different language in the profile dropdown
- **THEN** the locale SHALL update immediately in the UI
- **AND** the preference SHALL be persisted via `PATCH /api/me` to the backend

#### Scenario: Language loaded from profile on login
- **WHEN** a user logs in on a new device or browser
- **THEN** the application SHALL fetch the user's locale preference from `GET /api/me`
- **AND** apply it to the UI, overriding any localStorage value

### Requirement: Authenticated API Calls
All frontend API calls SHALL include the user's Entra ID access token as a Bearer token in the Authorization header.

#### Scenario: API call with valid token
- **WHEN** the frontend makes an API request
- **THEN** the request SHALL include `Authorization: Bearer <access_token>` header
- **AND** the backend SHALL accept the request if the token is valid

#### Scenario: API call returns 401
- **WHEN** the backend returns HTTP 401 (token expired or invalid)
- **THEN** the frontend SHALL attempt silent token renewal via MSAL
- **AND** retry the request with the new token

## MODIFIED Requirements

### Requirement: Web Application Shell
The sidebar SHALL include navigation items for Dashboard, Notes, Ideas, Research, Specs, Development, Voice, and Agents. The Specs item SHALL use a file-code icon. The Development item SHALL use a Code icon and be positioned after Specs and before Agents. The site header SHALL display a user profile menu in the top-right position replacing the standalone language toggle.

#### Scenario: Specs nav item visible
- **WHEN** the sidebar is rendered
- **THEN** a "Specs" navigation item is visible between Research and Development

#### Scenario: Navigate to development
- **WHEN** the user clicks Development in the sidebar
- **THEN** the application SHALL navigate to /development

#### Scenario: Header shows user profile instead of language toggle
- **WHEN** the site header is rendered for an authenticated user
- **THEN** the language toggle SHALL be replaced by the user profile menu component
