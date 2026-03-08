"""Text chat endpoint — uses Azure OpenAI with tool calling via the supervisor agent."""

import json
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from app.agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)
router = APIRouter()

_supervisor: SupervisorAgent | None = None


def set_supervisor(supervisor: SupervisorAgent) -> None:
    global _supervisor
    _supervisor = supervisor


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ToolNotification(BaseModel):
    action: str       # e.g. "create_note", "get_notes"
    agent: str        # e.g. "Notes Agent"
    summary: str      # e.g. "Created note 'Pick kids up'"


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolNotification] = []


SYSTEM_PROMPT = (
    "You are Turbo, a helpful AI assistant. You can manage notes, brainstorm ideas, "
    "do research, create development specs, and manage development tasks for the user. "
    "Development tasks have a 4-stage pipeline: Plan, Build, Run, Test. "
    "Be concise and helpful. When you perform an action, confirm what you did. "
    "Always respond in a natural, human-readable way. Never show IDs, GUIDs, or raw data "
    "structures to the user. When you create something, confirm with its title or name. "
    "When listing items, show them as a clean, readable list. Format responses for a chat interface. "
    "IMPORTANT LINKING RULE: When the user asks to research an idea or generate specs from an idea, "
    "you MUST first call get_idea or get_ideas to obtain the idea's ID, then pass that ID as the "
    "'idea_id' parameter when calling web_search, deep_research, or generate_spec. "
    "IMPORTANT STATUS RULE: Always check the 'status' field in function results. "
    "If status is 'pending' or 'started', the task is NOT done — tell the user it's still in progress. "
    "If status is 'completed', offer to read or review the results."
)


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    if _supervisor is None:
        raise HTTPException(status_code=503, detail="Supervisor not initialized")

    user_id = getattr(request.state, "user_id", "default-user")

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

    if not endpoint or not api_key:
        raise HTTPException(status_code=503, detail="Azure OpenAI not configured")

    from urllib.parse import urlparse
    parsed = urlparse(endpoint)
    base_url = f"{parsed.scheme}://{parsed.hostname}"

    client = AsyncAzureOpenAI(
        azure_endpoint=base_url,
        api_key=api_key,
        api_version="2025-01-01-preview",
    )

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in req.history[-20:]:  # Keep last 20 messages
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    tools = _supervisor.tool_definitions
    executed_tools: list[ToolNotification] = []

    # Allow up to 5 rounds of tool calling
    for _ in range(5):
        try:
            resp = await client.chat.completions.create(
                model=deployment,
                messages=messages,
                tools=tools if tools else None,
                temperature=0.7,
                max_completion_tokens=1024,
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            # Retry without tools as fallback
            resp = await client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=1024,
            )

        choice = resp.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            # Process tool calls
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = tc.function.arguments
                logger.info("Chat tool call: %s(%s)", fn_name, fn_args[:100])
                try:
                    result, agent_name = await _supervisor.handle_function_call(fn_name, fn_args, user_id=user_id)
                    try:
                        parsed_result = json.loads(result)
                        if isinstance(parsed_result, dict):
                            title = parsed_result.get("title") or parsed_result.get("name") or ""
                            summary = f"{fn_name.replace('_', ' ').title()}: {title}" if title else fn_name.replace('_', ' ').title()
                        elif isinstance(parsed_result, list):
                            summary = f"Found {len(parsed_result)} items"
                        else:
                            summary = fn_name.replace('_', ' ').title()
                    except Exception:
                        summary = fn_name.replace('_', ' ').title()
                    executed_tools.append(ToolNotification(action=fn_name, agent=agent_name, summary=summary))
                except Exception as e:
                    result = json.dumps({"error": str(e)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            continue  # Let the model process tool results

        # Final text response
        return ChatResponse(
            reply=choice.message.content or "I completed the action.",
            tool_calls=executed_tools,
        )

    # Fallback if too many tool rounds
    return ChatResponse(
        reply="I processed your request. Let me know if you need anything else.",
        tool_calls=executed_tools,
    )
