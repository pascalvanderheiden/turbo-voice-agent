# Delta Spec: web-app

## ADDED Requirements

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
