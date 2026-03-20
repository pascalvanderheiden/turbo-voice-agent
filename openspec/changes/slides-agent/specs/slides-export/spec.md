## ADDED Requirements

### Requirement: PDF upload to blob storage
The system SHALL upload the exported PDF to blob storage under the path slides/{task_id}/export.pdf after the export stage completes.

#### Scenario: Successful upload
- **WHEN** PDF export completes
- **THEN** system uploads PDF to blob storage and stores the blob URL on the dev-task

### Requirement: PDF preview in dev-task detail
The system SHALL display an embedded PDF preview in the dev-task detail view when a slides task has completed the export stage.

#### Scenario: View exported PDF
- **WHEN** user opens a completed slides dev-task
- **THEN** detail view shows embedded PDF viewer with page navigation below the terminal output

#### Scenario: PDF not yet available
- **WHEN** user opens a slides dev-task still in init or slides stage
- **THEN** PDF preview section shows "PDF will be available after export completes"

### Requirement: PDF download
The system SHALL allow users to download the exported PDF file directly from the dev-task detail view.

#### Scenario: Download PDF
- **WHEN** user clicks download button on a completed slides task
- **THEN** browser downloads the PDF file with filename "{presentation-title}.pdf"

### Requirement: Source code download
The system SHALL allow users to download the generated deck-engine source code as a zip archive from the dev-task detail view.

#### Scenario: Download source code
- **WHEN** user clicks "Download Code" on a completed slides task
- **THEN** system zips the workspace directory and serves it for download

### Requirement: Export artifacts stored on dev-task
The system SHALL store export artifact URLs (PDF URL, code archive URL) on the dev-task model for retrieval.

#### Scenario: Artifacts populated after export
- **WHEN** export stage completes
- **THEN** dev-task's artifacts field contains pdfUrl and codeUrl pointing to blob storage
