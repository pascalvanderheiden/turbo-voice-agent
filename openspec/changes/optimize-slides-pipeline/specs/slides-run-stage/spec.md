## ADDED Requirements

### Requirement: Run stage installs dependencies
The run stage SHALL execute `npm install` in the deck directory before starting the dev server.

#### Scenario: Successful npm install
- **WHEN** the run stage begins after the slides stage completes
- **THEN** the system runs `npm install` in the deck directory and waits for it to complete successfully

#### Scenario: npm install failure
- **WHEN** `npm install` fails with a non-zero exit code
- **THEN** the run stage reports the error in the pipeline output and marks the stage as failed

### Requirement: Run stage starts dev server
The run stage SHALL start `npm run dev` in the deck directory, which launches the Slidev dev server on port 3333.

#### Scenario: Dev server starts successfully
- **WHEN** `npm install` completes successfully
- **THEN** the system runs `npm run dev` in the deck directory as a long-running process

#### Scenario: Dev server health check
- **WHEN** the dev server process is started
- **THEN** the system polls the sandbox proxy at `/proxy/3333/` until a successful response is received or a 60-second timeout expires

### Requirement: Run stage exposes preview URL
After the dev server is confirmed running, the run stage SHALL report the live preview URL in the pipeline output.

#### Scenario: Preview URL reported
- **WHEN** the dev server health check succeeds
- **THEN** the pipeline output includes the preview URL in the format `/api/dev/{task_id}/preview/`

#### Scenario: Dev server timeout
- **WHEN** the dev server does not respond within 60 seconds
- **THEN** the run stage reports a warning but does not fail the pipeline (the server may still be starting)
