"""Supervisor Agent — routes tasks to specialist agents via function calling."""

import json
import logging

from app.agents.brainstorm_agent import BrainstormAgent
from app.agents.dev_agent import DevAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.notes_agent import NotesAgent
from app.agents.research_agent import ResearchAgent
from app.agents.skills_agent import SkillsAgent
from app.agents.slides_agent import SlidesAgent
from app.agents.spec_agent import SpecAgent
from app.agents.todo_agent import TodoAgent

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Supervisor that routes incoming requests to the appropriate specialist agent."""

    def __init__(
        self,
        notes_agent: NotesAgent,
        brainstorm_agent: BrainstormAgent | None = None,
        research_agent: ResearchAgent | None = None,
        spec_agent: SpecAgent | None = None,
        dev_agent: DevAgent | None = None,
        skills_agent: SkillsAgent | None = None,
        marketing_agent: MarketingAgent | None = None,
        todo_agent: TodoAgent | None = None,
        slides_agent: SlidesAgent | None = None,
    ):
        self._notes_agent = notes_agent
        self._brainstorm_agent = brainstorm_agent
        self._research_agent = research_agent
        self._spec_agent = spec_agent
        self._dev_agent = dev_agent
        self._skills_agent = skills_agent
        self._marketing_agent = marketing_agent
        self._todo_agent = todo_agent
        self._slides_agent = slides_agent
        self._agents: dict[str, object] = {"notes": notes_agent}
        if brainstorm_agent:
            self._agents["brainstorm"] = brainstorm_agent
        if slides_agent:
            self._agents["slides"] = slides_agent
        if research_agent:
            self._agents["research"] = research_agent
        if spec_agent:
            self._agents["spec"] = spec_agent
        if dev_agent:
            self._agents["dev"] = dev_agent
        if skills_agent:
            self._agents["skills"] = skills_agent
        if marketing_agent:
            self._agents["marketing"] = marketing_agent
        if todo_agent:
            self._agents["todo"] = todo_agent

    @property
    def tool_definitions(self) -> list[dict]:
        """Return all tool definitions from all registered agents."""
        tools: list[dict] = []
        for agent in self._agents.values():
            tools.extend(agent.tool_definitions)
        return tools

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> tuple[str, str]:
        """Route a function call to the appropriate agent.

        Returns (result_json, agent_name).
        """
        notes_functions = {
            "create_note", "get_notes", "get_note", "update_note", "delete_note",
        }
        brainstorm_functions = {
            "create_idea", "get_ideas", "get_idea", "update_idea", "delete_idea", "refine_idea",
        }
        research_functions = {
            "web_search", "deep_research", "get_research_list", "get_research", "delete_research",
        }
        spec_functions = {
            "create_spec", "get_specs", "get_spec", "update_spec", "delete_spec",
            "generate_spec", "optimize_spec", "add_feature_to_spec",
        }
        dev_functions = {
            "create_dev_task", "get_dev_tasks", "get_dev_task", "delete_dev_task",
            "trigger_dev_pipeline",
        }
        skills_functions = {
            "install_skill", "uninstall_skill", "search_skills", "list_skills",
        }
        marketing_functions = {
            "create_marketing_video", "get_marketing_videos", "get_marketing_video",
            "delete_marketing_video", "trigger_video_generation",
        }
        todo_functions = {
            "create_todo", "get_todos", "get_todo", "update_todo", "delete_todo", "complete_todo",
        }
        slides_functions = {
            "create_slides", "get_slides_list", "get_slides", "update_slides",
            "delete_slides", "refine_slides",
        }

        if function_name in notes_functions:
            logger.info("Routing '%s' to Notes Agent", function_name)
            result = await self._notes_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Notes Agent"

        if function_name in brainstorm_functions and self._brainstorm_agent:
            logger.info("Routing '%s' to Brainstorm Agent", function_name)
            result = await self._brainstorm_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Brainstorm Agent"

        if function_name in research_functions and self._research_agent:
            logger.info("Routing '%s' to Research Agent", function_name)
            result = await self._research_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Research Agent"

        if function_name in spec_functions and self._spec_agent:
            logger.info("Routing '%s' to Spec Agent", function_name)
            result = await self._spec_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Spec Agent"

        if function_name in dev_functions and self._dev_agent:
            logger.info("Routing '%s' to Turbo Dev Agent", function_name)
            result = await self._dev_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Turbo Dev Agent"

        if function_name in skills_functions and self._skills_agent:
            logger.info("Routing '%s' to Skills Agent", function_name)
            result = await self._skills_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Skills Agent"

        if function_name in marketing_functions and self._marketing_agent:
            logger.info("Routing '%s' to Marketing Agent", function_name)
            result = await self._marketing_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Marketing Agent"

        if function_name in todo_functions and self._todo_agent:
            logger.info("Routing '%s' to Todo Agent", function_name)
            result = await self._todo_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Todo Agent"

        if function_name in slides_functions and self._slides_agent:
            logger.info("Routing '%s' to Slides Agent", function_name)
            result = await self._slides_agent.handle_function_call(function_name, arguments, user_id=user_id)
            return result, "Slides Agent"

        logger.warning("Unknown function: %s", function_name)
        return json.dumps(
            {
                "error": f"I don't know how to handle '{function_name}'. "
                "I can help with notes, brainstorming ideas, slide presentations, research, specs, development tasks, "
                "skills management, marketing videos, and to-do tasks."
            }
        ), "Supervisor"
