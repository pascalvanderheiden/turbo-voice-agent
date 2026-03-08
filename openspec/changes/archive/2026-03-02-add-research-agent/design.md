## Context
The research agent adds a third specialist to the agent team. It uses two different models via the Azure OpenAI Responses API:
- **Web search**: gpt-4.1 (East US 2, already deployed) with `web_search_preview` tool — fast, real-time lookups
- **Deep research**: o3-deep-research (West US, separate endpoint) with `web_search_preview` tool — multi-step, comprehensive

Research entries are stored in-memory (same pattern as notes/ideas) and can optionally link to a brainstorm idea.

## Goals
- Quick web search via voice or UI for real-time info
- Deep research mode for thorough investigation with citations
- Link research results to brainstorm ideas for enrichment
- Same CRUD + voice + UI pattern as notes and ideas

## Non-Goals
- Persistent research history across restarts (future: Cosmos DB)
- Scheduled/recurring research
- Research on private/internal documents (future: Azure AI Search RAG)

## Decisions

### Two separate OpenAI clients for different regions
- gpt-4.1 is deployed in East US 2 (existing Foundry endpoint)
- o3-deep-research is only available in West US (separate Foundry endpoint)
- Each uses its own endpoint + API key configured via env vars
- Alternative: Single region (not possible — o3-deep-research unavailable in East US 2)

### Uses OpenAI Responses API (not Chat Completions)
- Web search requires the Responses API with `web_search_preview` tool type
- The `client.responses.create()` method returns structured output with `web_search_call` items and `url_citation` annotations
- Alternative: Custom Bing Search API integration (more code, same cost)

### Research entries stored as flat documents
- Each research has: id, title, query, mode (web_search | deep_research), result (markdown), citations (list of {url, title}), optional ideaId, timestamps
- When linked to an idea, the idea's detail view shows related research
- Alternative: Embed research in idea document (limits standalone research)

### Deep research runs synchronously but with long timeout
- o3-deep-research can take minutes; the REST endpoint uses a longer timeout
- Voice mode triggers research and notifies on completion
- Alternative: Background job queue (overkill for local dev)

## Risks / Trade-offs
- o3-deep-research can be slow (minutes) — UI needs clear loading state
- Bing grounding costs per search call — documented in pricing
- West US endpoint adds second set of credentials to manage
- In-memory storage loses research on restart

## Open Questions
- Should deep research results be exportable (PDF/markdown)?
- Should we rate-limit deep research calls to control costs?
