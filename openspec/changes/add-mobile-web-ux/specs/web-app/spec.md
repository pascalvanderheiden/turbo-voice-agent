## MODIFIED Requirements

### Requirement: Web Application Shell
The application layout SHALL be responsive. On viewports below 768px (mobile), the sidebar SHALL be hidden and replaced by a bottom tab bar. The site header SHALL be simplified to show only the logo and a settings icon. On viewports 768px and above (desktop), the existing sidebar and header SHALL remain unchanged.

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

## ADDED Requirements

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
