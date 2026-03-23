## MODIFIED Requirements

### Requirement: Deck config fields on Slides model
The Slides model SHALL include deck configuration fields: subtitle (str), icon (str, emoji), theme (str, default "shadcn/ui"), appearance (str, default "dark"), and palette (str, default "arctic"). These fields SHALL be user-editable and used by the init stage.

#### Scenario: Slides created with deck config defaults
- **WHEN** a new slides presentation is created
- **THEN** the model SHALL have default values: theme="shadcn/ui", appearance="dark", palette="arctic", subtitle="", icon=""

### Requirement: PowerPoint-only attachments field
The Slides model attachments field SHALL only store `.pptx` file URLs. The images field SHALL be removed from the model.

#### Scenario: Attachments contain only PowerPoint
- **WHEN** the user updates attachments on a slides spec
- **THEN** only `.pptx` URLs SHALL be accepted in the attachments array

## REMOVED Requirements

### Requirement: Upload images and PDFs
**Reason**: Replaced by PowerPoint-only attachments. Images and PDFs are no longer used as slide context.
**Migration**: Existing `images` field is removed. Existing `attachments` field accepts only `.pptx` files.
