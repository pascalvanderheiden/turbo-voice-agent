## MODIFIED Requirements

### Requirement: Web Application Shell
The sidebar SHALL include navigation items for Dashboard, Notes, Ideas, Research, Specs, Voice, and Agents. The Specs item SHALL use a file-code icon.

#### Scenario: Specs nav item visible
- **WHEN** the sidebar is rendered
- **THEN** a "Specs" navigation item is visible between Research and Voice

### Requirement: Notes Management UI
The dashboard SHALL display summary cards for notes, ideas, research, and specs counts. The specs card SHALL link to the /specs page.

#### Scenario: Specs card on dashboard
- **WHEN** the dashboard loads
- **THEN** a Specs card shows the total number of specs and links to /specs

## ADDED Requirements

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
