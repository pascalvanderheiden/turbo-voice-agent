## MODIFIED Requirements

### Requirement: Init stage uses deck config from slides spec
The init stage SHALL execute `npx create-deckio <deck-name>` with the title, subtitle, icon, theme, appearance, and palette values parsed from the refined draft's Deck Config section instead of hardcoded values.

#### Scenario: Init with custom deck config
- **WHEN** the refined draft contains Deck Config with title "GitHub Copilot", subtitle "The Basics", theme "shadcn/ui", appearance "dark", palette "forest"
- **THEN** the init stage SHALL run `npx -y create-deckio@latest <deck-name> --title 'GitHub Copilot' --subtitle 'The Basics' --theme shadcn/ui --appearance dark --palette forest --yes`

### Requirement: Single autopilot invocation for slides stage
The slides stage SHALL execute a single Copilot CLI invocation with autopilot mode, passing the entire refined slide content as the prompt, instead of iterating slide-by-slide.

#### Scenario: Slides generated in one pass
- **WHEN** the slides stage runs with refined content containing 10 slides
- **THEN** the system SHALL execute one `copilot --experimental --yolo --autopilot --model <model> --agent squad -p "<full refined slides content>"` command

### Requirement: PowerPoint template porting
When a `.pptx` attachment exists on the slides spec, the slides stage SHALL run a follow-up `copilot --continue -p "/deck-port-powerpoint <blob-url>"` command after the main slides invocation.

#### Scenario: PowerPoint template applied
- **WHEN** the slides spec has a `.pptx` attachment at URL `https://storage.blob.core.windows.net/slides/template.pptx`
- **THEN** the system SHALL run `copilot --continue -p "/deck-port-powerpoint https://storage.blob.core.windows.net/slides/template.pptx"` after the main slides generation

#### Scenario: No PowerPoint attached
- **WHEN** the slides spec has no `.pptx` attachments
- **THEN** the system SHALL skip the PowerPoint porting step

### Requirement: Screenshot-based export
The export stage SHALL run `npm run dev`, navigate each slide route with Playwright, and take PNG screenshots of every slide. Screenshots SHALL be stored on the dev-task via the existing screenshot mechanism.

#### Scenario: Export captures all slides
- **WHEN** the export stage runs on a deck with 8 slides
- **THEN** the system SHALL start the dev server, take a screenshot of each slide route, and store all screenshots on the dev-task

## REMOVED Requirements

### Requirement: PDF export to blob storage
**Reason**: Replaced by screenshot-based export. Screenshots are more useful for preview and the existing dev-task screenshot mechanism already handles storage.
**Migration**: Export artifacts no longer contain pdfUrl. Screenshots are stored via `_collect_screenshots()`.
