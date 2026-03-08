# marketing-service Specification

## Purpose
TBD - created by archiving change add-marketing-agent. Update Purpose after archive.
## Requirements
### Requirement: Marketing Video Storage
The system SHALL store marketing videos with title, devTaskId, specId, status, videoPath, scriptContent, durationSeconds, error, and timestamps.

#### Scenario: Create marketing video linked to dev task
- **WHEN** a user creates a marketing video with a title and devTaskId
- **THEN** the system SHALL create a video record with status "pending"
- **AND** the devTaskId SHALL reference an existing dev task with completed screenshots

#### Scenario: Create marketing video without dev task
- **WHEN** a user creates a marketing video without a devTaskId
- **THEN** the system SHALL return an error indicating a dev task link is required

### Requirement: Marketing Video CRUD Operations
The system SHALL provide REST endpoints for managing marketing videos.

#### Scenario: List all marketing videos
- **WHEN** `GET /api/marketing` is called
- **THEN** the system SHALL return all marketing videos ordered by creation date descending

#### Scenario: Get single marketing video
- **WHEN** `GET /api/marketing/{id}` is called with a valid ID
- **THEN** the system SHALL return the full marketing video including script content and status

#### Scenario: Delete marketing video
- **WHEN** `DELETE /api/marketing/{id}` is called
- **THEN** the system SHALL remove the video record and delete the video file from disk

#### Scenario: Stream marketing video
- **WHEN** `GET /api/marketing/{id}/video` is called for a completed video
- **THEN** the system SHALL stream the MP4 file with support for HTTP Range requests (seeking)

### Requirement: Video Generation Pipeline
The system SHALL generate promotional videos using a multi-stage pipeline: Script → Generate → Compose → Store.

#### Scenario: Trigger video generation
- **WHEN** a video generation pipeline is triggered for a marketing video
- **THEN** the system SHALL load the linked dev task's screenshots and spec content
- **AND** generate a software promotion script using GPT-5.2
- **AND** send the script + reference screenshots to Sora-2 for video generation
- **AND** compose the output into a single ~3-minute MP4

#### Scenario: Pipeline failure handling
- **WHEN** any stage of the pipeline fails
- **THEN** the system SHALL set the video status to "failed" with the error message
- **AND** clean up any partial video files

#### Scenario: Script content preservation
- **WHEN** the script stage completes successfully
- **THEN** the system SHALL store the generated script in the video record's scriptContent field
- **AND** the script SHALL focus on software promotion: problem statement, feature walkthrough, design quality, and call-to-action

### Requirement: Bidirectional Dev Task Linking
The system SHALL maintain bidirectional links between marketing videos and dev tasks.

#### Scenario: Dev task detail shows marketing videos
- **WHEN** a dev task has linked marketing videos
- **THEN** the dev task detail page SHALL display a "Marketing Videos" section with links to each video

#### Scenario: Delete dev task with marketing videos
- **WHEN** a dev task with linked marketing videos is deleted
- **THEN** the marketing video records SHALL be orphaned (devTaskId preserved but task no longer exists)

