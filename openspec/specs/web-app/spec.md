# web-app Specification

## Purpose
TBD - created by archiving change add-voice-agent-foundation. Update Purpose after archive.
## Requirements
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
- **AND** the language toggle SHALL be replaced by the user profile menu component

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
The web frontend SHALL provide a complete brainstorm ideas management interface with list, create, edit, delete, and refine capabilities.

#### Scenario: Ideas list view
- **WHEN** the user navigates to the Ideas page
- **THEN** a data table SHALL display all ideas with columns: title, status (draft/refined), image count, updated date
- **AND** each row SHALL have action buttons for edit, delete, and refine

#### Scenario: Create idea with images
- **WHEN** the user clicks "New Idea"
- **THEN** a dialog SHALL appear with fields for title, description, and an image upload area (drag & drop, click to browse, camera on mobile)
- **AND** on submit, the idea SHALL be created via the REST API

#### Scenario: Refine idea
- **WHEN** the user clicks "Refine" on an idea
- **THEN** the system SHALL call `POST /api/ideas/{id}/refine` and display the refined draft in a detail view
- **AND** a loading state SHALL be shown during GPT-5.2 processing

#### Scenario: View refined draft
- **WHEN** the user opens a refined idea
- **THEN** the detail view SHALL render the refined draft as formatted markdown alongside the original description and images

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
The web app SHALL provide a Specs page with full CRUD operations, an "Optimize with AI" button for draft specs, and a detail view showing structured markdown content. Specs SHALL be grouped by type: foundation spec shown prominently at the top, feature specs listed below.

#### Scenario: View spec list
- **WHEN** the user navigates to /specs
- **THEN** the foundation spec (if any) is shown at the top, followed by feature specs, each with title, status badge (draft/optimized), source idea link, and timestamps

#### Scenario: Create spec manually
- **WHEN** the user clicks "New Spec" and selects type (foundation/feature), fills in title and content
- **THEN** the spec is created with status "draft"

#### Scenario: Generate specs from idea
- **WHEN** the user clicks "Convert to spec" on an idea detail view
- **THEN** the system generates a foundation spec plus a minimal set of feature specs from the idea content using GPT-5.2 and navigates to the specs page

#### Scenario: Optimize draft spec
- **WHEN** the user clicks "Optimize with AI" on a draft spec
- **THEN** the spec content is refined by GPT-5.2 and the status changes to "optimized"

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

