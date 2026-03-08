## 1. Backend — Research Models
- [ ] 1.1 Create `Research` Pydantic models (ResearchBase, ResearchCreate, Research) with fields: title, query, mode, result, citations, ideaId
- [ ] 1.2 Create `ResearchCreate` with title, query, mode (web_search | deep_research), optional ideaId

## 2. Backend — Research Service
- [ ] 2.1 Create `InMemoryResearchService` with CRUD (create, list, get_by_id, delete)
- [ ] 2.2 Add `list_by_idea(idea_id)` method to filter research linked to an idea
- [ ] 2.3 Add `set_result(id, result, citations)` method to store search results

## 3. Backend — Web Search Implementation
- [ ] 3.1 Create `research_client.py` with two OpenAI client factories (East US 2 for gpt-4.1, West US for o3-deep-research)
- [ ] 3.2 Implement `web_search(query)` using Responses API with gpt-4.1 + web_search_preview tool
- [ ] 3.3 Implement `deep_research(query)` using Responses API with o3-deep-research + web_search_preview tool
- [ ] 3.4 Parse response to extract output_text and url_citation annotations into structured result

## 4. Backend — Research Agent
- [ ] 4.1 Create `ResearchAgent` with tool definitions: `create_research`, `get_research_list`, `get_research`, `delete_research`, `web_search`, `deep_research`
- [ ] 4.2 Implement `handle_function_call` routing to ResearchService and search functions
- [ ] 4.3 `web_search` tool: creates entry, runs search, stores result, returns summary
- [ ] 4.4 `deep_research` tool: creates entry, runs deep research, stores result, returns summary

## 5. Backend — Supervisor Update
- [ ] 5.1 Register `ResearchAgent` in supervisor
- [ ] 5.2 Add research function routing in `handle_function_call`
- [ ] 5.3 Return `"Research Agent"` as agent name for notifications

## 6. Backend — Research REST Routes
- [ ] 6.1 Create `GET /api/research` (list all), `GET /api/research/{id}` (get one), `DELETE /api/research/{id}`
- [ ] 6.2 Create `POST /api/research/search` (trigger web search with query + optional ideaId)
- [ ] 6.3 Create `POST /api/research/deep` (trigger deep research with query + optional ideaId)
- [ ] 6.4 Create `GET /api/ideas/{id}/research` route to list research linked to an idea

## 7. Backend — Voice Session Update
- [ ] 7.1 Add research tool definitions to voice session tools
- [ ] 7.2 Update voice instructions to mention research capabilities
- [ ] 7.3 Update EN/NL greetings to mention research

## 8. Backend — Environment Config
- [ ] 8.1 Add `AZURE_OPENAI_WESTUS_ENDPOINT` and `AZURE_OPENAI_WESTUS_API_KEY` to .env
- [ ] 8.2 Update .env.example with new vars
- [ ] 8.3 Wire up research service and agent in main.py

## 9. Frontend — API Types
- [ ] 9.1 Add `Research`, `ResearchCreate` interfaces to api.ts
- [ ] 9.2 Add `researchApi` methods (list, get, delete, search, deepResearch, listByIdea)

## 10. Frontend — Research Page
- [ ] 10.1 Create `/research` page with list table (title, mode, linked idea, date)
- [ ] 10.2 Create research detail view with rendered markdown result and citation links
- [ ] 10.3 Create search dialog (query input, mode toggle: web search / deep research, optional idea link)
- [ ] 10.4 Add delete functionality
- [ ] 10.5 Show loading state for deep research (can take minutes)

## 11. Frontend — Idea-Research Link
- [ ] 11.1 Show linked research entries on idea detail view
- [ ] 11.2 Add "Research this idea" button on idea detail that pre-fills the query

## 12. Frontend — Navigation & i18n
- [ ] 12.1 Add "Research" to sidebar navigation
- [ ] 12.2 Add research-related translation keys (EN/NL)
- [ ] 12.3 Add research action labels for notifications
- [ ] 12.4 Add research card to dashboard
