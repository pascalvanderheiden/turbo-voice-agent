## MODIFIED Requirements

### Requirement: Slides pipeline stages
The slides pipeline SHALL use three stages in order: `init`, `slides`, `run`.

#### Scenario: Stage order
- **WHEN** a slides dev-task is created
- **THEN** the task has exactly three stages: `init`, `slides`, `run`

### Requirement: Init stage scaffolds deck and syncs skills
The init stage SHALL run `npx create-deckio@latest <deck_name>` with parameters from the Slides entity (title, subtitle, theme, appearance, palette), verify the deck directory, initialize git, and sync skills from blob storage.

#### Scenario: Successful init with Slides entity config
- **WHEN** the init stage runs with a linked Slides entity that has theme, appearance, and palette fields
- **THEN** the system runs `npx create-deckio@latest <deck_name> --title '<title>' --subtitle '<subtitle>' --theme <theme> --appearance <appearance> --palette <palette> --yes`
- **AND** verifies the deck directory contains a `.github/` folder
- **AND** initializes a git repository in the deck directory
- **AND** syncs skills from blob storage into the sandbox

#### Scenario: Init with default config
- **WHEN** the Slides entity does not have theme/appearance/palette fields
- **THEN** the system uses defaults: theme=default, appearance=dark, palette=blue

### Requirement: Slides stage uses Copilot autopilot session
The slides stage SHALL `cd` into the deck directory and run `copilot --autopilot --yolo` with a prompt to create slides from the Slides entity content.

#### Scenario: Slide generation from content
- **WHEN** the slides stage runs with a Slides entity that has a refined draft with a `## Slides` section
- **THEN** the system runs `copilot --autopilot --yolo` in the deck directory with a prompt containing the slides content

#### Scenario: PowerPoint attachment import
- **WHEN** the Slides entity has a `.pptx` attachment
- **THEN** the slides prompt includes instructions to use the `deck-port-powerpoint` skill to import the PowerPoint content as input for slide generation

### Requirement: Deck name sanitization
The deck directory name SHALL be derived from the task title by lowercasing, replacing spaces with hyphens, stripping non-alphanumeric characters (except hyphens), collapsing consecutive hyphens, trimming leading/trailing hyphens, and truncating to 30 characters.

#### Scenario: Title with special characters
- **WHEN** the task title is "SlideDeck: GitHub Copilot — The Basics"
- **THEN** the deck name is `slidedeck-github-copilot-the-b`
