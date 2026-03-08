"""Research Agent — specialist agent for web search and deep research."""

import asyncio
import json
import logging

from app.models.research import ResearchCreate
from app.services.memory_research_service import InMemoryResearchService
from app.services.research_client import run_deep_research, run_web_search

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Agent that handles research operations."""

    def __init__(self, research_service: InMemoryResearchService):
        self._service = research_service

    @property
    def tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for real-time information on a topic. Returns a summary with source citations. Use for quick factual lookups. The search runs in the background — tell the user it has started.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query"},
                            "idea_id": {"type": "string", "description": "Optional: link this research to a brainstorm idea by its ID"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "deep_research",
                    "description": "Perform comprehensive deep research on a topic. The AI agent will search many sources, read pages, and synthesize findings into a detailed report with citations. Takes several minutes. The research runs in the background — tell the user it has started and they can check results later.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The research question or topic"},
                            "idea_id": {"type": "string", "description": "Optional: link this research to a brainstorm idea by its ID"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_research_list",
                    "description": "List all research entries",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_research",
                    "description": "Get a specific research entry by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "research_id": {"type": "string", "description": "The research entry ID"},
                        },
                        "required": ["research_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_research",
                    "description": "Delete a research entry by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "research_id": {"type": "string", "description": "The research entry ID"},
                        },
                        "required": ["research_id"],
                    },
                },
            },
        ]

    async def _run_search_background(self, entry_id: str, query: str, search_fn) -> None:
        """Run search in background and update entry when done."""
        try:
            result_text, citations = await search_fn(query)
            await self._service.set_result(entry_id, result_text, citations)
            logger.info("Background research %s completed", entry_id)
        except Exception as e:
            logger.exception("Background research %s failed", entry_id)
            await self._service.set_failed(entry_id, str(e))

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        if function_name == "web_search":
            query = args.get("query", "")
            idea_id = args.get("idea_id")
            entry = await self._service.create(
                ResearchCreate(query=query, mode="web_search", ideaId=idea_id)
            )
            asyncio.create_task(self._run_search_background(entry.id, query, run_web_search))
            return json.dumps({
                "success": True,
                "status": "started",
                "research": {"id": entry.id, "title": entry.title},
                "message": "Web search has been started and is running in the background. "
                "The status is currently PENDING — it is not yet complete. "
                "Tell the user you've started the search and will notify them when results are ready.",
            })

        elif function_name == "deep_research":
            query = args.get("query", "")
            idea_id = args.get("idea_id")
            entry = await self._service.create(
                ResearchCreate(query=query, mode="deep_research", ideaId=idea_id)
            )
            asyncio.create_task(self._run_search_background(entry.id, query, run_deep_research))
            return json.dumps({
                "success": True,
                "status": "started",
                "research": {"id": entry.id, "title": entry.title},
                "message": "Deep research has been started and is running in the background. "
                "This takes several minutes. The status is currently PENDING — it is not yet complete. "
                "Tell the user you've started deep research and will notify them when results are ready.",
            })

        elif function_name == "get_research_list":
            entries = await self._service.list()
            return json.dumps({
                "research": [
                    {"id": r.id, "title": r.title, "mode": r.mode, "status": r.status}
                    for r in entries
                ],
                "status_guidance": "Items with status 'pending' are still running — do NOT say they are done. "
                "Only offer to read results for items with status 'completed'.",
            })

        elif function_name == "get_research":
            entry = await self._service.get_by_id(args.get("research_id", ""))
            if entry:
                status_msg = ""
                if entry.status == "pending":
                    status_msg = "This research is still PENDING — it has not completed yet. Tell the user it's still in progress."
                elif entry.status == "failed":
                    status_msg = "This research FAILED. Tell the user it encountered an error."
                else:
                    status_msg = "This research is COMPLETED. You can offer to read the results."
                return json.dumps({
                    "research": {
                        "id": entry.id, "title": entry.title,
                        "mode": entry.mode, "status": entry.status,
                        "result": (entry.result or "")[:500] if entry.status == "completed" else None,
                        "citation_count": len(entry.citations) if entry.status == "completed" else 0,
                    },
                    "status_guidance": status_msg,
                })
            return json.dumps({"error": "Research not found"})

        elif function_name == "delete_research":
            deleted = await self._service.delete(args.get("research_id", ""))
            return json.dumps({"success": deleted})

        return json.dumps({"error": f"Unknown function: {function_name}"})
