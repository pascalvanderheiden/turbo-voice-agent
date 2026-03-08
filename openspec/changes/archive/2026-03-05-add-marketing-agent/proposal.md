# Proposal: Add Marketing Agent

## Summary
Add a new Marketing Agent that generates promotional videos for apps built by the Turbo Dev Agent. The agent uses the **Sora-2** model deployed on Azure AI Foundry (East US 2) to produce a ~3-minute video showcasing the application's key features. It leverages the linked spec content and Playwright screenshots from the dev task as source material for the video.

## Motivation
After the Turbo Dev Agent builds an application mockup with screenshots, there's no way to create promotional material. A Marketing Agent closes this gap by auto-generating a polished video walkthrough that can be shared with stakeholders, embedded in pitch decks, or used for social media.

## Scope

### In Scope
- New `MarketingAgent` specialist agent with Sora-2 video generation
- New `MarketingVideo` data model and `InMemoryMarketingService` (with JSON persistence)
- New REST routes (`/api/marketing`) for CRUD + trigger + video streaming
- Voice integration via Supervisor Agent (new tools: `create_marketing_video`, `get_marketing_videos`, `get_marketing_video`, `delete_marketing_video`, `trigger_video_generation`)
- Bidirectional linking between marketing videos and dev tasks (similar to spec↔devTask pattern)
- Frontend page for marketing videos with video player, status tracking, and linked dev task navigation
- Sidebar navigation entry for Marketing
- Agent overview update (new agent card with Sora-2 model reference)

### Out of Scope
- Video editing/trimming UI
- Custom voiceover or narration selection (future enhancement)
- Distribution/publishing to external platforms
- Mobile app support (web only for now)

## Architecture

```
DevTask (screenshots + archive)
        ↓
Marketing Agent ← Spec content + skill context
        ↓
  Sora-2 (Azure AI Foundry, East US 2)
        ↓
  MP4 video → stored on disk → streamed via /api/marketing/{id}/video
```

### Video Generation Pipeline
1. **Gather** — Load linked dev task, extract screenshots (base64 → images), load spec content (foundation + features)
2. **Script** — Use GPT-5.2 to generate a video script/storyboard from the spec + screenshots, focusing on software promotion (feature highlights, UI walkthrough, value proposition)
3. **Generate** — Send script + reference images to Sora-2 API to produce video segments
4. **Compose** — Concatenate segments into a single ~3-min MP4
5. **Store** — Save video file to `data/marketing/` directory, update artifact reference

### Key Design Decisions
- **Sora-2 deployment**: Dedicated Azure AI Foundry deployment in East US 2 (separate from main OpenAI endpoint)
- **Storage**: Local filesystem (same pattern as dev task archives), not blob storage
- **Streaming**: Video served via FastAPI `StreamingResponse` for in-app playback
- **Linking**: `MarketingVideo.devTaskId` → `DevTask`, similar to `DevTask.specId` → `Spec`

## Environment Variables

| Variable | Description |
|---|---|
| `SORA_ENDPOINT` | Azure AI Foundry endpoint for Sora-2 (East US 2) |
| `SORA_API_KEY` | API key for the Sora-2 deployment |
| `SORA_DEPLOYMENT` | Deployment name (default: `sora-2`) |

## Affected Capabilities
- `agent-orchestration` — Add Marketing Agent to supervisor routing + agent overview
- `web-app` — New marketing page, sidebar entry, video player component
- New capability: `marketing-service`

## Risks
- Sora-2 API may have long generation times (minutes); pipeline must handle timeouts gracefully
- Video file sizes could be large (~100-500MB for 3 min); streaming endpoint must support range requests
- Sora-2 image-to-video capabilities may have input format constraints; screenshot pre-processing may be needed
