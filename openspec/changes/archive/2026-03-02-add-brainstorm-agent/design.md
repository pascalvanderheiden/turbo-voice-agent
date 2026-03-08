## Context
The brainstorm agent introduces a second specialist in the agent team. It uses GPT-5.2 (chat completions, not realtime) to refine ideas into structured drafts. Image uploads are stored locally (`/uploads/`) in dev; Azure Blob Storage in production.

## Goals
- Brainstorm agent refines raw ideas into dev-ready drafts with gap analysis
- Image/camera support for both ideas and notes
- Same CRUD + voice pattern as notes for consistency
- Minimal new dependencies

## Non-Goals
- Real-time collaborative brainstorming (multi-user)
- Image generation or editing
- OCR/image-to-text extraction (future enhancement)

## Decisions

### Brainstorm Agent uses GPT-5.2 via Chat Completions
- The refine action sends the idea + optional image to GPT-5.2 with a system prompt that produces: summary, gaps/questions, and a development-ready draft
- Alternatives: Using the realtime model (too expensive for text processing), using a local model (not available)

### Image storage: local filesystem in dev, Azure Blob in production
- Images saved to `backend/uploads/` with UUID filenames
- Served via static file mount at `/uploads/`
- Model receives image as base64 in the chat completion (GPT-5.2 supports vision)
- Alternative: Always use Blob Storage (adds complexity for local dev)

### Shared upload endpoint
- Single `POST /api/upload` endpoint returns `{ "url": "/uploads/<uuid>.<ext>" }`
- Both notes and ideas reference images by URL string array
- Alternative: Separate endpoints per entity (unnecessary duplication)

## Risks / Trade-offs
- GPT-5.2 API cost per refine call → mitigate by only refining on explicit user action, not auto
- Image size → limit to 10MB per upload, max 5 images per entity
- In-memory storage loses images on restart → acceptable for local dev

## Open Questions
- Should refined drafts be versioned (keep history of refinements)?
- Should the voice agent be able to trigger image capture on mobile?
