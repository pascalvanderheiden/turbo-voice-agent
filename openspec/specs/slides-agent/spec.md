## MODIFIED Requirements

### Requirement: Concise slide refinement
The refine method SHALL produce a structured output with two sections: (1) a Deck Config block containing title, subtitle, icon, theme, appearance, and palette, and (2) a numbered Slides list where each slide has a title and at most 2 sentences of content.

#### Scenario: Refinement produces concise output
- **WHEN** the user refines a presentation with title "GitHub Copilot — The Basics" and description "A slidedeck explaining Copilot features"
- **THEN** the refined draft SHALL contain a `## Deck Config` section with YAML-formatted fields (title, subtitle, icon, theme, appearance, palette) and a `## Slides` section with numbered slides each having a title and max 2 sentences

#### Scenario: Research and attachments inform content
- **WHEN** the presentation has linked research or PowerPoint attachments
- **THEN** the refinement SHALL incorporate that context into the slide content but still keep each slide to 2 sentences max

### Requirement: PowerPoint-only attachments
The slides agent SHALL only accept `.pptx` files as attachments. PDF and image attachments SHALL be rejected. PowerPoint files serve as style/layout templates for the deck.

#### Scenario: PowerPoint file accepted
- **WHEN** a user attaches a `.pptx` file to a presentation
- **THEN** the system SHALL store the file URL in the attachments array

#### Scenario: Non-PowerPoint file rejected
- **WHEN** a user attempts to attach a `.pdf` or image file
- **THEN** the system SHALL reject the upload with an error indicating only `.pptx` files are accepted

### Requirement: Deck config extracted during refinement
The refine method SHALL extract deck configuration (title, subtitle, icon, theme, appearance, palette) as a separate structured block in the refined output, distinct from the slide content.

#### Scenario: Deck config in refined output
- **WHEN** refinement completes
- **THEN** the refined draft SHALL contain a Deck Config section with fields: title, subtitle, icon (emoji), theme (default: shadcn/ui), appearance (default: dark), palette (default: arctic)
