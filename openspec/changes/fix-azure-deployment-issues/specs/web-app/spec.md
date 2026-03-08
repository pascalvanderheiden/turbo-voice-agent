## MODIFIED Requirements

### Requirement: Dashboard Summary Cards
The dashboard SHALL display summary cards for Notes, Ideas, Research, Specs, and Marketing. Each card SHALL show the count of items and link to the respective list page. The Marketing card SHALL use the IconVideo (Tabler) icon and link to `/marketing`, displaying the total count of marketing videos from `GET /api/marketing`.

#### Scenario: Dashboard displays all summary cards including Marketing
- **WHEN** a user navigates to the Dashboard
- **THEN** summary cards for Notes, Ideas, Research, Specs, and Marketing SHALL be displayed
- **AND** each card SHALL show the current count of items
- **AND** the Marketing card SHALL link to `/marketing`

### Requirement: Ideas Management
The Ideas list SHALL display each idea with its title, status, image count, and date. When an idea has linked specs, the list SHALL show a link to the foundational spec only (not individual feature specs), since the foundational spec already contains links to its child feature specs. Clicking the foundational spec link SHALL navigate to the spec detail view.

#### Scenario: Idea with linked specs shows only foundational spec link
- **WHEN** an idea has been converted to specs (foundation + features)
- **THEN** the Ideas list SHALL display a single link to the foundational spec
- **AND** SHALL NOT display individual links to feature specs
- **AND** clicking the link SHALL navigate to the foundational spec detail view

#### Scenario: Idea without linked specs
- **WHEN** an idea has not been converted to specs
- **THEN** no spec links SHALL be displayed for that idea

### Requirement: Specs Management UI
The Specs list SHALL display each spec with its title only (without the type suffix such as "- Foundation" or "- Feature"). The spec type SHALL be indicated via a badge or tag only in the spec detail view. Foundation specs SHALL be displayed at the top of the list, followed by feature specs grouped under their parent.

#### Scenario: Spec list shows clean titles without type suffix
- **WHEN** a user views the Specs list
- **THEN** each spec SHALL display only its title (e.g., "My App" not "My App - Foundation")
- **AND** foundation specs SHALL appear at the top of the list

#### Scenario: Spec detail shows type indicator
- **WHEN** a user clicks on a spec to view its details
- **THEN** the detail view SHALL show a Foundation or Feature badge/indicator
- **AND** feature specs SHALL display their linked parent foundation spec
- **AND** the foundation spec detail SHALL list its child feature specs

### Requirement: User Profile Menu
The User Profile menu SHALL display the user's profile photo (if uploaded), display name, email, and language selector. The menu SHALL include options for uploading or changing a profile picture. When no profile picture is uploaded, the menu SHALL display the user's initials as a fallback avatar.

#### Scenario: User with profile picture
- **WHEN** a user has uploaded a profile picture
- **THEN** the header dropdown SHALL display the profile photo instead of initials
- **AND** the photo SHALL be loaded from `GET /api/me/photo`

#### Scenario: User without profile picture
- **WHEN** a user has not uploaded a profile picture
- **THEN** the header dropdown SHALL display the user's initials as avatar

## ADDED Requirements

### Requirement: Profile Picture Upload
The web application SHALL provide a profile picture upload interface in the User Profile page. Users SHALL be able to upload, preview, and crop their profile photo. The uploaded photo SHALL be stored via the backend and displayed throughout the application (header, marketing videos). Supported formats SHALL be PNG, JPG, JPEG, and WEBP with a maximum file size of 5MB.

#### Scenario: Upload profile picture
- **WHEN** a user navigates to the User Profile page and uploads a photo
- **THEN** the application SHALL display a preview of the selected image
- **AND** submit the photo to `POST /api/me/photo`
- **AND** update the header avatar immediately upon successful upload

#### Scenario: Profile picture used in marketing
- **WHEN** a marketing video is generated for a user who has a profile picture
- **THEN** the profile picture SHALL be available to the marketing-service as a personalization asset

#### Scenario: Invalid profile picture upload
- **WHEN** a user attempts to upload a file that exceeds 5MB or is not a supported format
- **THEN** the application SHALL display a validation error without submitting to the backend

### Requirement: Marketing Sidebar Navigation
The sidebar navigation SHALL include a "Marketing" entry with the IconVideo (Tabler) icon, positioned between "Development" and "Skills" (or the next navigation item). Clicking it SHALL navigate to `/marketing`.

#### Scenario: Marketing navigation item visible
- **WHEN** a user views the sidebar navigation
- **THEN** a "Marketing" entry SHALL be visible with the IconVideo icon
- **AND** clicking it SHALL navigate to `/marketing`
