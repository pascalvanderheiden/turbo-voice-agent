# Change: Add Research Agent with Web Search and Deep Research

## Why
Users need a research capability to investigate topics using real-time web data. Research can be standalone or linked to brainstorm ideas, enriching them with grounded, citation-backed findings. Two modes cover different needs: quick web search (gpt-4.1 + web_search_preview) and deep research (o3-deep-research).

## What Changes
- New research service with in-memory storage for research entries (title, query, mode, result, citations, optional idea link)
- New Research Agent registered in supervisor with tools: `create_research`, `get_research_list`, `get_research`, `delete_research`, `web_search`, `deep_research`
- `web_search` uses gpt-4.1 (East US 2) + `web_search_preview` tool via Responses API for fast lookups
- `deep_research` uses o3-deep-research (West US) + `web_search_preview` tool via Responses API for comprehensive investigation
- REST API: CRUD for research entries + trigger endpoints for search/deep-research
- Research entries can optionally link to an idea via `ideaId`
- Frontend: Research page with list, detail view (rendered markdown + citations), create dialog, delete
- Voice mode: research tools exposed for voice-triggered searches
- i18n: EN/NL translation keys for research UI

## Impact
- Affected specs: research-service (new), agent-orchestration, realtime-voice, web-app
- New env vars: `AZURE_OPENAI_WESTUS_ENDPOINT`, `AZURE_OPENAI_WESTUS_API_KEY` for o3-deep-research
- Existing East US 2 endpoint with gpt-4.1 deployment used for web search
- Bing grounding costs apply for web_search_preview tool usage
