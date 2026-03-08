# Tasks: Fix Azure Deployment Issues & Add Missing Features

## 1. Observability & Logging (do first — enables debugging all other fixes)
- [x] 1.1 Add structured JSON logging with correlation IDs across all backend services
- [x] 1.2 Add request/response logging middleware to FastAPI with trace context
- [x] 1.3 Add pipeline stage logging in dev-service (stage start, complete, fail with durations)
- [x] 1.4 Add skill operation logging in brainstorm-service (install, delete, search with userId)
- [x] 1.5 Integrate Azure Application Insights (OpenTelemetry SDK) for production tracing
- [x] 1.6 Add log correlation between frontend API calls and backend processing

## 2. Dev Task Pipeline Fix
- [x] 2.1 Investigate and fix pipeline stages not being triggered after task creation in production
- [x] 2.2 Add detailed logging around background task spawning and execution
- [x] 2.3 Fix dev task deletion endpoint error
- [ ] 2.4 Verify fix in deployed environment with end-to-end test

## 3. Skills Storage Fix
- [x] 3.1 Fix userId resolution — ensure authenticated user ID is used instead of "default-user"
- [x] 3.2 Fix skill file storage to use Azure Blob Storage in production
- [ ] 3.3 Verify skills appear correctly in Cosmos DB with proper userId
- [ ] 3.4 Verify skill files are accessible on Blob Storage

## 4. Dashboard Marketing Tile
- [x] 4.1 Add Marketing summary card to Dashboard page
- [x] 4.2 Wire up marketing count from `GET /api/marketing` endpoint
- [x] 4.3 Link card to /marketing route

## 5. Idea-to-Spec Link Simplification
- [x] 5.1 Update Ideas list/detail to link only to the foundational spec
- [x] 5.2 Remove individual feature spec links from ideas view (foundation spec already links to its features)

## 6. Spec Title Display Fix
- [x] 6.1 Update spec list to show only the spec name (without "- Foundation" or "- Feature" suffix)
- [x] 6.2 Keep type indicator (Foundation/Feature badge) visible only in the spec detail view

## 7. User Profile Picture
- [x] 7.1 Add profile picture upload endpoint to backend (`POST /api/me/photo`, `GET /api/me/photo`)
- [x] 7.2 Store profile pictures on Azure Blob Storage
- [x] 7.3 Add photo upload UI to User Profile page (crop/preview)
- [x] 7.4 Display profile photo in header dropdown (replacing initials when available)
- [x] 7.5 Make profile photo available to marketing-service for video personalization
