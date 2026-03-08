# Tasks: Add Marketing Agent

## Phase 1: Data Model & Service
- [x] Create `backend/app/models/marketing.py` — `MarketingVideo`, `MarketingVideoCreate` Pydantic models with fields: id, title, devTaskId, specId, status (pending/generating/completed/failed), videoPath, scriptContent, error, createdAt, updatedAt
- [x] Create `backend/app/services/memory_marketing_service.py` — `InMemoryMarketingService` with JSON persistence, CRUD ops, `list_by_dev_task(dev_task_id)` method
- [x] Add `devTaskId` linking: when creating a marketing video linked to a dev task, store the reference bidirectionally

## Phase 2: Marketing Agent
- [x] Create `backend/app/agents/marketing_agent.py` — `MarketingAgent` class with tool definitions for voice integration
- [x] Implement `_generate_script()` — Use GPT-5.2 to create a software promo video script from spec content + screenshot descriptions
- [x] Implement `_generate_video()` — Call Sora-2 API (Azure AI Foundry, East US 2) with script + reference screenshots to produce video segments
- [x] Implement `_compose_video()` — Concatenate Sora-2 output into single MP4 (~3 min)
- [x] Implement `run_pipeline(video_id)` — Orchestrate: gather → script → generate → compose → store
- [x] Add tool definitions: `create_marketing_video`, `get_marketing_videos`, `get_marketing_video`, `delete_marketing_video`, `trigger_video_generation`

## Phase 3: REST API & Wiring
- [x] Create `backend/app/routes/marketing.py` — CRUD routes + trigger endpoint + `/api/marketing/{id}/video` streaming endpoint (StreamingResponse with range request support)
- [x] Wire in `backend/app/main.py` — Initialize marketing service + agent, register routes, add to supervisor routing, update agent overview with Sora-2 model info
- [x] Update `backend/app/agents/supervisor_agent.py` — Route marketing functions to Marketing Agent

## Phase 4: Frontend
- [x] Add `MarketingVideo` type to `frontend/src/lib/api.ts` with fetch helpers
- [x] Create `frontend/src/app/(app)/marketing/page.tsx` — List page with video cards showing title, status, linked dev task, thumbnail
- [x] Create `frontend/src/app/(app)/marketing/[id]/page.tsx` — Detail page with HTML5 video player, script display, linked dev task card, generation status timeline
- [x] Add Marketing entry to sidebar navigation in `frontend/src/components/sidebar.tsx`
- [x] Add marketing link/badge to dev task detail page (`frontend/src/app/(app)/development/[id]/page.tsx`)

## Phase 5: Voice Integration
- [x] Add marketing tools to voice WebSocket tool list in `backend/app/routes/voice_ws.py`
- [x] Test voice flow: "Create a marketing video for my app" → creates video linked to most recent dev task → triggers pipeline

## Phase 6: Documentation
- [x] Update `README.md` prerequisites with Sora-2 deployment info
- [x] Update environment variables table with `SORA_ENDPOINT`, `SORA_API_KEY`, `SORA_DEPLOYMENT`
