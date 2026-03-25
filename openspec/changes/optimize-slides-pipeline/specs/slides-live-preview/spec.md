## MODIFIED Requirements

### Requirement: Live preview served by run pipeline stage
The live preview SHALL be served by the dev server started during the `run` pipeline stage, not by a separate "start live" action.

#### Scenario: Auto-preview after run stage
- **WHEN** the run pipeline stage completes successfully
- **THEN** the preview URL is available immediately without requiring user action
- **AND** the frontend auto-displays the preview iframe

#### Scenario: Preview URL lookup
- **WHEN** the frontend requests a live preview for a task whose run stage has completed
- **THEN** the backend returns the proxy URL `/api/dev/{task_id}/preview/` without starting a new dev server

### Requirement: Preview proxy routes to sandbox
The backend SHALL proxy preview requests through the sandbox's existing `/proxy/3333/` endpoint.

#### Scenario: Successful preview proxy
- **WHEN** a request is made to `/api/dev/{task_id}/preview/{path}`
- **THEN** the backend proxies to `{sandbox_url}/proxy/3333/{path}` and returns the response

#### Scenario: Dev server not running
- **WHEN** a preview request is made but the run stage has not completed
- **THEN** the backend returns a clear error message indicating the pipeline has not reached the run stage yet
