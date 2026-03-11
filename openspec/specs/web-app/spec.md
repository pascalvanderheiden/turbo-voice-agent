# web-app Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
### Requirement: Web Application Shell
The application layout SHALL be responsive. On viewports below 768px (mobile), the sidebar SHALL be hidden and replaced by a bottom tab bar. The site header SHALL be simplified to show only the logo and a settings icon. On viewports 768px and above (desktop), the existing sidebar and header SHALL remain unchanged. The sidebar SHALL include navigation items for Dashboard, Notes, Ideas, Research, Specs, Development, Voice, and Agents. The Specs item SHALL use a file-code icon. The Development item SHALL use a Code icon and be positioned after Specs and before Agents. The site header SHALL display a user profile menu in the top-right position replacing the standalone language toggle.

#### Scenario: Specs nav item visible
- **WHEN** the sidebar is rendered
- **THEN** a "Specs" navigation item is visible between Research and Development

#### Scenario: Navigate to development
- **WHEN** the user clicks Development in the sidebar
- **THEN** the application SHALL navigate to /development

#### Scenario: Header shows user profile instead of language toggle
- **WHEN** the site header is rendered for an authenticated user
- **AND** the language toggle SHALL be replaced by the user profile menu component

#### Scenario: Mobile layout hides sidebar
- **WHEN** the viewport width is below 768px
- **THEN** the sidebar SHALL NOT be rendered
- **AND** a bottom tab bar SHALL be displayed at the bottom of the screen with fixed positioning

#### Scenario: Desktop layout unchanged
- **WHEN** the viewport width is 768px or above
- **THEN** the sidebar and header SHALL render as they do today
- **AND** the bottom tab bar SHALL NOT be rendered

#### Scenario: Mobile header simplified
- **WHEN** the viewport width is below 768px
- **THEN** the site header SHALL display only the Turbo Agent logo (left) and a settings gear icon (right)
- **AND** the settings icon SHALL open a menu with profile, theme, language, and notifications

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
The User Profile menu SHALL display the user's profile photo (if uploaded), display name, email, and language selector. The menu SHALL include options for uploading or changing a profile picture. When no profile picture is uploaded, the menu SHALL display the user's initials as a fallback avatar.

#### Scenario: User with profile picture
- **WHEN** a user has uploaded a profile picture
- **THEN** the header dropdown SHALL display the profile photo instead of initials
- **AND** the photo SHALL be loaded from `GET /api/me/photo`

#### Scenario: User without profile picture
- **WHEN** a user has not uploaded a profile picture
- **THEN** the header dropdown SHALL display the user's initials as avatar

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

### Requirement: Notes Management UI
The dashboard SHALL display summary cards for notes, ideas, research, and specs counts. The specs card SHALL link to the /specs page.

#### Scenario: Specs card on dashboard
- **WHEN** the dashboard loads
- **THEN** a Specs card shows the total number of specs and links to /specs

### Requirement: Voice Mode Interface
The web frontend SHALL provide a voice mode page with an animated voice orb and real-time audio communication.

#### Scenario: Voice mode page layout
- **WHEN** the user navigates to Voice Mode
- **THEN** the page SHALL display a centered voice orb on a dark background with minimal surrounding UI

#### Scenario: Voice orb idle state
- **WHEN** the voice session is not active or is waiting for input
- **THEN** the orb SHALL display a subtle breathing pulse animation (1-2s cycle) using the brand gradient

#### Scenario: Voice orb listening state
- **WHEN** the user is speaking (microphone active, speech detected)
- **THEN** the orb SHALL display responsive wave ripples that react to audio input amplitude

#### Scenario: Voice orb thinking state
- **WHEN** the voice agent is processing (between speech stop and response start)
- **THEN** the orb SHALL display a swirling/rotating motion

#### Scenario: Voice orb speaking state
- **WHEN** the voice agent is producing audio output
- **THEN** the orb SHALL display rhythmic pulsing synchronized with the audio output

#### Scenario: Voice orb error state
- **WHEN** a voice connection error occurs
- **THEN** the orb SHALL briefly shake and flash with a red tint

#### Scenario: WebSocket audio connection
- **WHEN** the user activates voice mode
- **THEN** the frontend SHALL open a WebSocket to `/ws/voice`, request microphone permission, capture audio as PCM16 at 24kHz, and stream in ~50ms chunks

#### Scenario: Conversation transcript
- **WHEN** the voice agent speaks or the user speaks
- **THEN** a transcript area below the orb SHALL display the conversation history with user and agent turns

### Requirement: Voice Activation Button
The web frontend SHALL provide a quick-access voice activation button in the site header.

#### Scenario: Voice button in header
- **WHEN** the user is on any page
- **THEN** a circular voice activation button (soundwave icon) SHALL be visible in the site header
- **AND** clicking it SHALL navigate to or activate the voice mode

### Requirement: Brainstorm Ideas Management UI
The Ideas list SHALL display each idea with its title, status, image count, and date. When an idea has linked specs, the list SHALL show a link to the foundational spec only (not individual feature specs), since the foundational spec already contains links to its child feature specs. Clicking the foundational spec link SHALL navigate to the spec detail view.

#### Scenario: Idea with linked specs shows only foundational spec link
- **WHEN** an idea has been converted to specs (foundation + features)
- **THEN** the Ideas list SHALL display a single link to the foundational spec
- **AND** SHALL NOT display individual links to feature specs
- **AND** clicking the link SHALL navigate to the foundational spec detail view

#### Scenario: Idea without linked specs
- **WHEN** an idea has not been converted to specs
- **THEN** no spec links SHALL be displayed for that idea

### Requirement: Image Upload Component
The web frontend SHALL provide a reusable image upload component used by both notes and ideas.

#### Scenario: Upload via drag and drop
- **WHEN** the user drags an image file onto the upload area
- **THEN** the file SHALL be uploaded to `/api/upload` and a preview thumbnail displayed

#### Scenario: Upload via file browser
- **WHEN** the user clicks the upload area
- **THEN** a file picker SHALL open, filtered to image types

#### Scenario: Remove uploaded image
- **WHEN** the user clicks the remove button on a thumbnail
- **THEN** the image SHALL be removed from the entity's images list

### Requirement: Research Management UI
The web frontend SHALL provide a research management interface with search trigger, list, detail view, and delete capabilities.

#### Scenario: Research list view
- **WHEN** the user navigates to the Research page
- **THEN** a data table SHALL display all research entries with columns: title, mode (web search / deep research), linked idea, date
- **AND** each row SHALL be clickable to view the full result

#### Scenario: Trigger new research
- **WHEN** the user clicks "New Research"
- **THEN** a dialog SHALL appear with a query input, mode toggle (web search / deep research), and optional idea selector
- **AND** on submit, the research SHALL be triggered via the REST API

#### Scenario: Research detail view
- **WHEN** the user clicks on a research entry
- **THEN** the detail view SHALL render the result as formatted markdown with clickable citation links

#### Scenario: Deep research loading state
- **WHEN** deep research is in progress
- **THEN** the UI SHALL show a clear loading indicator explaining it may take several minutes

#### Scenario: Delete research
- **WHEN** the user clicks delete on a research entry
- **THEN** a confirmation dialog SHALL appear and on confirmation the entry SHALL be deleted

### Requirement: Idea-Research Integration
The idea detail view SHALL display linked research entries and allow triggering research from an idea.

#### Scenario: Show linked research on idea
- **WHEN** the user views an idea that has linked research
- **THEN** the detail view SHALL show a "Research" section listing all linked research entries

#### Scenario: Research from idea
- **WHEN** the user clicks "Research this idea" on an idea detail view
- **THEN** the research dialog SHALL open with the idea's title pre-filled as the query and the ideaId pre-linked

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

### Requirement: Development Page
The web application SHALL provide a Development page for managing development tasks with pipeline tracking. Tasks SHALL display their mode (Mock/Sequence), iteration progress, linked spec information, and selected skills. The detail page SHALL display iterations with their individual stage pipelines and plan output.

#### Scenario: View development task list
- **WHEN** the user navigates to /development
- **THEN** the page SHALL display all dev tasks in a card grid
- **AND** each card SHALL show the task title, linked spec name, overall status, and a 4-stage progress indicator (Plan, Build, Run, Test)
- **AND** status badges SHALL use yellow for pending, blue for running, green for completed, red for failed

#### Scenario: Show task mode
- **WHEN** a user views the development task list
- **THEN** each task SHALL display a badge indicating its mode ("Mock" or "Sequence")

#### Scenario: Show iteration progress in sequence mode
- **WHEN** a sequence mode task is displayed
- **THEN** the task SHALL show iteration progress (e.g., "2/5 iterations completed")
- **AND** the current iteration label SHALL be visible

#### Scenario: View development task detail
- **WHEN** the user clicks on a dev task
- **THEN** the detail page SHALL show a pipeline visualization with all 4 stages
- **AND** each stage SHALL show its status, output/logs, and duration
- **AND** screenshot artifacts SHALL be displayed as images
- **AND** a download button SHALL be available for the code archive when the task is completed
- **AND** selected skills SHALL be shown as badges in the header

#### Scenario: View iterations
- **WHEN** a user views a sequence mode task detail
- **THEN** iterations SHALL be displayed as a vertical timeline with tabs or sections
- **AND** each iteration SHALL show its label (foundation/feature name) and stage pipeline

#### Scenario: View plan output
- **WHEN** a user expands a Plan stage in any iteration
- **THEN** the plan output SHALL be rendered as formatted markdown content
- **AND** the plan SHALL clearly reference which spec part (foundation or feature) it covers

#### Scenario: Create development task manually
- **WHEN** the user clicks "New Development Task"
- **THEN** a dialog SHALL appear with title input, spec selector dropdown, mode selector, and skill selection chips
- **AND** submitting SHALL create the task with selected skills and optionally trigger the pipeline

#### Scenario: Trigger pipeline from detail page
- **WHEN** the user clicks "Run Pipeline" on a pending task
- **THEN** the pipeline SHALL start and the page SHALL poll for stage updates

### Requirement: Spec Detail Page Development Action
The spec detail page SHALL provide a "Develop" action button that creates a linked dev task.

#### Scenario: Create dev task from spec
- **WHEN** a user clicks "Develop" on a spec detail page
- **THEN** a dialog SHALL appear allowing the user to choose the pipeline mode (Mock or Sequence)
- **AND** upon confirmation, a dev task SHALL be created linked to the spec
- **AND** the spec card SHALL show a "In Development" badge with a link to the dev task

#### Scenario: View linked dev task
- **WHEN** a spec has a linked dev task
- **THEN** the spec card on the list page SHALL show a development status indicator
- **AND** clicking the indicator SHALL navigate to the linked dev task detail page

### Requirement: Skills Management UI on Agents Page
The agents page SHALL provide full skills lifecycle management: browse marketplace, install, delete, add local skills, and search — all with real-time notification feedback.

#### Scenario: Delete installed skill
- **WHEN** the user clicks the delete button on an installed skill card
- **THEN** a confirmation dialog SHALL appear
- **AND** on confirmation, `DELETE /api/agents/skills/{name}` SHALL be called
- **AND** a toast notification SHALL show "Skill deleted" on success
- **AND** the skills list SHALL auto-refresh

#### Scenario: Install marketplace skill
- **WHEN** the user clicks "Install" on a marketplace skill card
- **THEN** `POST /api/agents/skills/install` SHALL be called with the skill's repo and name
- **AND** a toast notification SHALL show "Installing {name}..."
- **AND** upon completion, the skill SHALL appear in the installed list with a "Skill installed" toast

#### Scenario: Search marketplace via backend proxy
- **WHEN** the user types in the skills search input
- **THEN** after 300ms debounce, `GET /api/agents/skills/search?q=<query>` SHALL be called
- **AND** results SHALL replace the marketplace grid with matching skills from skills.sh

#### Scenario: Add local skill
- **WHEN** the user clicks "Add Local Skill"
- **THEN** a dialog SHALL appear with path input and skill name input
- **AND** on submit, `POST /api/agents/skills/install-local` SHALL be called
- **AND** a toast notification SHALL confirm successful installation

#### Scenario: Marketplace card links
- **WHEN** marketplace skill cards are displayed
- **THEN** each card SHALL link to the correct skills.sh URL: `https://skills.sh/<owner>/<repo>/<skill-name>`
- **AND** clicking SHALL open the link in a new tab

### Requirement: Dev Task Skill Selection in Creation Dialog
The development task creation dialog SHALL allow users to select which installed skills the Dev Agent should use during code generation.

#### Scenario: Show skill chips in create dialog
- **WHEN** the user opens the "New Development Task" dialog
- **THEN** a "Skills" section SHALL display installed skills as toggleable chips
- **AND** each chip shows the skill name and can be toggled on/off

#### Scenario: Auto-suggest skills when spec selected
- **WHEN** the user selects a spec in the create dialog
- **THEN** `GET /api/dev/suggest-skills?specId=<id>` SHALL be called
- **AND** the suggested skills SHALL be pre-toggled as selected

#### Scenario: Show selected skills on dev task detail
- **WHEN** a dev task with selected skills is viewed on the detail page
- **THEN** the selected skill names SHALL be displayed as badges in the task header

### Requirement: Marketing Page
The web app SHALL include a marketing videos section accessible from the sidebar.

#### Scenario: Marketing list page
- **WHEN** the user navigates to `/marketing`
- **THEN** the page SHALL display a grid of marketing video cards showing title, status badge, linked dev task name, thumbnail (first frame or placeholder), and creation date

#### Scenario: Marketing detail page
- **WHEN** the user navigates to `/marketing/{id}`
- **THEN** the page SHALL display an HTML5 video player (if completed), the generated script, a link to the linked dev task, and a generation status timeline

#### Scenario: Video playback
- **WHEN** a completed marketing video is displayed
- **THEN** the video player SHALL support play/pause, seeking, fullscreen, and volume controls via the browser's native HTML5 video element
- **AND** the video source SHALL be `/api/marketing/{id}/video`

### Requirement: Sidebar Navigation Update
The sidebar SHALL include a Marketing entry with an appropriate icon.

#### Scenario: Marketing sidebar entry
- **WHEN** the sidebar is rendered
- **THEN** it SHALL include a "Marketing" link with IconVideo (Tabler) icon between Development and Skills entries

### Requirement: Dev Task Marketing Link
The dev task detail page SHALL show linked marketing videos.

#### Scenario: Dev task with marketing videos
- **WHEN** a dev task has one or more linked marketing videos
- **THEN** the detail page SHALL display a "Marketing Videos" section with cards linking to each video's detail page

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

### Requirement: Voice Activation Button
The web frontend SHALL provide a quick-access voice activation button. On desktop, this button is in the site header. On mobile, voice is a primary tab in the bottom tab bar.

#### Scenario: Voice button in header (desktop)
- **WHEN** the user is on any page on a desktop viewport
- **THEN** a circular voice activation button (soundwave icon) SHALL be visible in the site header
- **AND** clicking it SHALL navigate to or activate the voice mode

#### Scenario: Voice tab in bottom bar (mobile)
- **WHEN** the user is on any page on a mobile viewport
- **THEN** a Voice tab SHALL be visible in the bottom tab bar as one of the primary tabs
- **AND** tapping it SHALL navigate to the voice mode page

### Requirement: Bottom Tab Bar Navigation
On mobile viewports, the application SHALL display a bottom tab bar with five primary tabs: Notes, Ideas, Research, Specs, and Voice. Additional sections (Dashboard, Development, Marketing, Agents, Chat) SHALL be accessible via a "More" overflow menu triggered from the settings/menu icon.

#### Scenario: Primary tabs visible
- **WHEN** the viewport width is below 768px
- **THEN** the bottom tab bar SHALL display five tabs: Notes, Ideas, Research, Specs, Voice
- **AND** each tab SHALL have an icon and label
- **AND** the active tab SHALL be highlighted using the brand-pink accent color

#### Scenario: Touch targets meet minimum size
- **WHEN** the bottom tab bar is rendered on mobile
- **THEN** each tab target SHALL be at least 44px in height
- **AND** tabs SHALL have at minimum 8px horizontal spacing between them

#### Scenario: More menu for secondary navigation
- **WHEN** the user taps the settings icon in the mobile header
- **THEN** a slide-up menu SHALL appear with links to Dashboard, Development, Marketing, Agents, and Chat
- **AND** the menu SHALL include profile, theme toggle, and language selector

### Requirement: Mobile Entity CRUD
On mobile viewports, entity management (notes, ideas, research, specs) SHALL use a single-page pattern with inline bottom sheets for create, edit, and detail views instead of navigating to separate pages.

#### Scenario: View entity list on mobile
- **WHEN** the user is on an entity page (notes, ideas, research, or specs) on a mobile viewport
- **THEN** the full-width list SHALL be displayed without a sidebar
- **AND** each list item SHALL be touch-friendly with at least 44px tap target height

#### Scenario: View entity detail on mobile
- **WHEN** the user taps an entity in the list on mobile
- **THEN** a bottom sheet SHALL slide up showing the entity detail
- **AND** the sheet SHALL be dismissible by swiping down or tapping outside

#### Scenario: Create entity on mobile
- **WHEN** the user taps the create button (floating action button) on mobile
- **THEN** a bottom sheet SHALL slide up with the create form
- **AND** the form SHALL use full-width inputs optimized for touch

#### Scenario: Edit entity on mobile
- **WHEN** the user taps edit on an entity detail bottom sheet
- **THEN** the sheet content SHALL transition to an edit form
- **AND** save and cancel buttons SHALL be clearly visible at the bottom of the sheet

#### Scenario: Delete entity on mobile
- **WHEN** the user taps delete on an entity detail bottom sheet
- **THEN** a confirmation dialog SHALL appear
- **AND** the delete action button SHALL be positioned away from the easy thumb zone to prevent accidental deletion

### Requirement: Mobile Voice Mode
On mobile viewports, the voice mode page SHALL be a full-screen immersive experience with the voice orb centered and occupying 40-60% of the viewport width. The mobile header and bottom tab bar SHALL remain visible but minimal.

#### Scenario: Full-screen voice on mobile
- **WHEN** the user navigates to voice mode on a mobile viewport
- **THEN** the voice orb SHALL be centered on screen occupying 40-60% of viewport width
- **AND** the background SHALL be dark with minimal surrounding UI
- **AND** the transcript area SHALL be scrollable below the orb

#### Scenario: Voice overlay pill on mobile
- **WHEN** voice is active and the user navigates to another tab on mobile
- **THEN** a small floating pill indicator SHALL appear at the top of the screen
- **AND** the pill SHALL show the current voice state (listening/speaking) with a mini orb
- **AND** tapping the pill SHALL navigate back to the voice tab
- **AND** the pill SHALL include a stop button to disconnect

### Requirement: Mobile Detection Hook
The application SHALL provide a `useIsMobile()` hook that detects mobile viewports using `matchMedia` and is available to all components for conditional rendering.

#### Scenario: Hook detects mobile viewport
- **WHEN** the viewport width is below 768px
- **THEN** `useIsMobile()` SHALL return `true`

#### Scenario: Hook detects desktop viewport
- **WHEN** the viewport width is 768px or above
- **THEN** `useIsMobile()` SHALL return `false`

#### Scenario: Hook responds to viewport changes
- **WHEN** the viewport width changes across the 768px breakpoint (e.g., device rotation)
- **THEN** `useIsMobile()` SHALL update its return value reactively

