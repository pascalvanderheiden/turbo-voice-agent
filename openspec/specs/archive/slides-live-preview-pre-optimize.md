## ADDED Requirements

### Requirement: Run Live action starts sandbox dev server
The dev-task detail page SHALL have a "Run Live" button for slides mode tasks. When clicked, it SHALL start `npm run dev` in the sandbox workspace and expose the endpoint URL so the user can view the deck in their browser.

#### Scenario: Run Live starts server
- **WHEN** the user clicks "Run Live" on a completed or running slides dev-task
- **THEN** the system SHALL execute `npm run dev` in the deck workspace via the sandbox, expose the port, and display the live URL in the dev-task detail page

#### Scenario: Live preview accessible in browser
- **WHEN** the sandbox dev server is running and port is exposed
- **THEN** the user SHALL be able to open the URL in their browser to navigate the live slide deck

### Requirement: Run Live shows embedded preview
The dev-task detail page SHALL display an iframe or link to the live deck URL when the dev server is running.

#### Scenario: Live preview displayed
- **WHEN** the Run Live server is active
- **THEN** the detail page SHALL show the deck URL and optionally an embedded iframe preview
