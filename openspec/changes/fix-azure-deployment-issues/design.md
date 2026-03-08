# Design: Fix Azure Deployment Issues & Add Missing Features

## Context
The application is deployed on Azure Container Apps with Cosmos DB, Blob Storage, and AI Foundry integrations. Several features that work locally fail in production due to environment-specific issues (auth context, storage backends, background task execution). Additionally, the application lacks structured logging, making production debugging extremely difficult.

## Goals
- Fix all identified production bugs (dev pipeline, skills storage, deletion errors, spec titles)
- Add structured observability to enable future debugging
- Complete missing dashboard and profile features
- Maintain backward compatibility with existing data

## Non-Goals
- Redesign the overall architecture
- Migrate storage backends
- Change authentication providers

## Decisions

### Logging: OpenTelemetry + Azure Application Insights
- **Decision**: Use OpenTelemetry Python SDK with Azure Monitor exporter
- **Why**: Native Azure integration, distributed tracing across services, structured JSON logs with correlation IDs
- **Alternatives**: Python `logging` only (no distributed tracing), third-party APM (unnecessary complexity)

### Profile Pictures: Azure Blob Storage
- **Decision**: Store profile photos in a dedicated Blob Storage container (`profile-photos`)
- **Why**: Consistent with existing Blob Storage usage; CDN-friendly; no database bloat
- **Alternatives**: Base64 in Cosmos DB (too large), Azure Files (unnecessary complexity)

### Skill userId Fix: Auth Context Propagation
- **Decision**: Extract userId from the Entra ID token (already available in request context) and pass it through to all service layer calls
- **Why**: The token is already validated; `default-user` is a fallback that shouldn't be used in production
- **Investigation needed**: Check if the issue is in the auth middleware not extracting the user, or the service layer not receiving it

### Dev Pipeline Fix: Background Task Execution
- **Decision**: Investigate whether `asyncio.create_task()` or `BackgroundTasks` is failing silently in the Container Apps environment
- **Investigation needed**: Check if the issue is related to async event loop lifecycle in production (e.g., Uvicorn worker recycling, container scaling)

## Risks / Trade-offs
- **Logging overhead**: Minimal; structured logging adds <1ms per request. Application Insights sampling can be tuned.
- **Profile picture storage**: Adds Blob Storage dependency for user service; mitigated by existing Blob Storage infrastructure.
- **Pipeline fix**: Root cause unknown until logging is in place; may require multiple iterations.

## Open Questions
- Is the dev pipeline issue related to Container Apps scaling/cold starts?
- Are skill files expected on Blob Storage or Azure Files share?
- Should profile pictures have size/format constraints beyond what the upload endpoint validates?
